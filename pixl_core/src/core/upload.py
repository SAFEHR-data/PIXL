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
from typing import TYPE_CHECKING, BinaryIO

from decouple import config

if TYPE_CHECKING:
    from core.exports import ParquetExport
    from core.project_config import PixlConfig


from core._secrets import AzureKeyVault
from core._upload_ftps import (
    _connect_to_ftp,
    _create_and_set_as_cwd,
    _create_and_set_as_cwd_multi_path,
)
from core.db.queries import get_project_slug_from_hashid, update_exported_at

logger = logging.getLogger(__name__)


class Uploader(ABC):
    """Upload strategy interface."""

    @abstractmethod
    def __init__(self, project_config: PixlConfig) -> None:
        """
        Initialise the uploader for a specific project with the destination configuration and an
        AzureKeyvault instance. The keyvault is used to fetch the secrets required to connect to
        the remote destination.

        :param project: The project name for which the uploader is being initialised. Used to fetch
            the correct secrets from the keyvault.
        """
        self.project_config = project_config
        self.keyvault = AzureKeyVault()


class FTPSUploader(Uploader):
    """Upload strategy for an FTPS server."""

    def __init__(self, project_config: PixlConfig) -> None:
        """Initialise the uploader with the destination configuration."""
        Uploader.__init__(self, project_config)
        self._set_config()

    def _set_config(self) -> None:
        # Use the Azure KV alias as prefix if it exists, otherwise use the project name
        az_prefix = self.project_config.project.azure_kv_alias
        az_prefix = az_prefix if az_prefix else self.project_config.project.name

        self.host = self.keyvault.fetch_secret(f"{az_prefix}--ftp--host")
        self.user = self.keyvault.fetch_secret(f"{az_prefix}--ftp--username")
        self.password = self.keyvault.fetch_secret(f"{az_prefix}--ftp--password")
        self.port = config("FTP_PORT", default=21, cast=int)

    def upload_dicom_image(self, zip_content: BinaryIO, pseudo_anon_id: str) -> None:
        """Upload a DICOM image to the FTPS server."""
        logger.info("Starting FTPS upload of '%s'", pseudo_anon_id)

        # rename destination to {project-slug}/{study-pseduonymised-id}.zip
        remote_directory = get_project_slug_from_hashid(pseudo_anon_id)

        # Create the remote directory if it doesn't exist
        ftp = _connect_to_ftp(self.host, self.port, self.user, self.password)
        _create_and_set_as_cwd(ftp, remote_directory)
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
        ftp = _connect_to_ftp(self.host, self.port, self.user, self.password)
        _create_and_set_as_cwd(ftp, parquet_export.project_slug)
        _create_and_set_as_cwd(ftp, parquet_export.extract_time_slug)
        _create_and_set_as_cwd(ftp, "parquet")

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
            _create_and_set_as_cwd(ftp, str(upload_root_dir))
            source_rel_path = source_path.relative_to(source_root_dir)
            source_rel_dir = source_rel_path.parent
            source_filename_only = source_rel_path.relative_to(source_rel_dir)
            _create_and_set_as_cwd_multi_path(ftp, source_rel_dir)
            with source_path.open("rb") as handle:
                command = f"STOR {source_filename_only}"

                # Store the file using a binary handler
                ftp.storbinary(command, handle)

        # Close the FTP connection
        ftp.quit()
        logger.info("Finished FTPS upload of files for '%s'", parquet_export.project_slug)
