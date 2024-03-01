#  Copyright (c) University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Functionality to upload files to a remote server."""

from __future__ import annotations

import ftplib
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Optional

from core.db.queries import get_project_slug_from_hashid, update_exported_at
from core.uploader._ftps import (
    connect_to_ftp,
    create_and_set_as_cwd,
    create_and_set_as_cwd_multi_path,
)
from core.uploader._secrets import AzureKeyVault

if TYPE_CHECKING:
    from core.exports import ParquetExport

logger = logging.getLogger(__name__)


class Uploader(ABC):
    """Upload strategy interface."""

    @abstractmethod
    def __init__(self, project_slug: str, keyvault_alias: Optional[str]) -> None:
        """
        Initialise the uploader for a specific project with the destination configuration and an
        AzureKeyvault instance. The keyvault is used to fetch the secrets required to connect to
        the remote destination.

        Child classes should implement the _set_config method to set the configuration for the
        upload strategy.

        :param :
        """
        self.project_slug = project_slug
        self.keyvault_alias = keyvault_alias
        self.keyvault = AzureKeyVault()
        self._set_config()

    @abstractmethod
    def _set_config(self) -> None:
        """Set the configuration for the uploader."""

    @abstractmethod
    def upload_dicom_image(self, *args: Any, **kwargs: Any) -> None:
        """
        Abstract method to upload DICOM images. To be overwritten by child classes.
        If an upload strategy does not support DICOM images, this method should raise a
        NotImplementedError.
        """

    @abstractmethod
    def upload_parquet_files(self, *args: Any, **kwargs: Any) -> None:
        """
        Abstract method to upload parquet files. To be overwritten by child classes.
        If an upload strategy does not support parquet files, this method should raise a
        NotImplementedError.
        """

    @staticmethod
    def create(project_slug: str, destination: str, keyvault_alias: Optional[str]) -> Uploader:
        """Create an uploader instance based on the destination."""
        choices: dict[str, type[Uploader]] = {"ftps": _FTPSUploader}
        try:
            return choices[destination](project_slug, keyvault_alias)

        except KeyError:
            error_msg = f"Destination '{destination}' is currently not supported"
            raise NotImplementedError(error_msg) from None


class _FTPSUploader(Uploader):
    """Upload strategy for an FTPS server."""

    def __init__(self, project_slug: str, keyvault_alias: Optional[str]) -> None:
        """Create instance of parent class"""
        super().__init__(project_slug, keyvault_alias)

    def _set_config(self) -> None:
        # Use the Azure KV alias as prefix if it exists, otherwise use the project name
        az_prefix = self.keyvault_alias
        az_prefix = az_prefix if az_prefix else self.project_slug

        self.host = self.keyvault.fetch_secret(f"{az_prefix}--ftp--host")
        self.user = self.keyvault.fetch_secret(f"{az_prefix}--ftp--username")
        self.password = self.keyvault.fetch_secret(f"{az_prefix}--ftp--password")
        self.port = int(self.keyvault.fetch_secret(f"{az_prefix}--ftp--port"))

    def upload_dicom_image(self, zip_content: BinaryIO, pseudo_anon_id: str) -> None:
        """Upload a DICOM image to the FTPS server."""
        logger.info("Starting FTPS upload of '%s'", pseudo_anon_id)

        # rename destination to {project-slug}/{study-pseduonymised-id}.zip
        remote_directory = get_project_slug_from_hashid(pseudo_anon_id)

        # Create the remote directory if it doesn't exist
        ftp = connect_to_ftp(self.host, self.port, self.user, self.password)
        create_and_set_as_cwd(ftp, remote_directory)
        command = f"STOR {pseudo_anon_id}.zip"
        logger.debug("Running %s", command)

        # Store the file using a binary handler
        try:
            ftp.storbinary(command, zip_content)
        except ftplib.all_errors as ftp_error:
            ftp.quit()
            error_msg = "Failed to run STOR command '%s': '%s'"
            raise ConnectionError(error_msg, command, ftp_error) from ftp_error

        # Close the FTP connection
        ftp.quit()

        # Update the exported_at timestamp in the PIXL database
        update_exported_at(pseudo_anon_id, datetime.now(tz=timezone.utc))
        logger.info("Finished FTPS upload of '%s'", pseudo_anon_id)

    def upload_parquet_files(self, parquet_export: ParquetExport) -> None:
        """
        Upload parquet to FTPS under <project name>/<extract datetime>/parquet.
        :param parquet_export: instance of the ParquetExport class
        The final directory structure will look like this:
        <project-slug>
        ├── <extract_datetime_slug>
        │   └── parquet
        │       ├── omop
        │       │   └── public
        │       │       └── PROCEDURE_OCCURRENCE.parquet
        │       └── radiology
        │           └── radiology.parquet
        ├── <pseudonymised_ID_DICOM_dataset_1>.zip
        └── <pseudonymised_ID_DICOM_dataset_2>.zip
        ...
        """
        logger.info("Starting FTPS upload of files for '%s'", parquet_export.project_slug)

        source_root_dir = parquet_export.current_extract_base
        # Create the remote directory if it doesn't exist
        ftp = connect_to_ftp(self.host, self.port, self.user, self.password)
        create_and_set_as_cwd(ftp, parquet_export.project_slug)
        create_and_set_as_cwd(ftp, parquet_export.extract_time_slug)
        create_and_set_as_cwd(ftp, "parquet")

        # get the upload root directory before we do anything as we'll need
        # to return to it (will it always be absolute?)
        upload_root_dir = Path(ftp.pwd())
        if not upload_root_dir.is_absolute():
            logger.error("server remote path is not absolute, what are we going to do?")

        # absolute paths of the source
        source_files = [x for x in source_root_dir.rglob("*.parquet") if x.is_file()]
        if not source_files:
            msg = f"No files found in {source_root_dir}"
            raise FileNotFoundError(msg)

        # throw exception if empty dir
        for source_path in source_files:
            create_and_set_as_cwd(ftp, str(upload_root_dir))
            source_rel_path = source_path.relative_to(source_root_dir)
            source_rel_dir = source_rel_path.parent
            source_filename_only = source_rel_path.relative_to(source_rel_dir)
            create_and_set_as_cwd_multi_path(ftp, source_rel_dir)
            with source_path.open("rb") as handle:
                command = f"STOR {source_filename_only}"

                # Store the file using a binary handler
                ftp.storbinary(command, handle)

        # Close the FTP connection
        ftp.quit()
        logger.info("Finished FTPS upload of files for '%s'", parquet_export.project_slug)
