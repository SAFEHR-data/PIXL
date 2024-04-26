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

"""Uploader subclass for FTPS."""

from __future__ import annotations

import ftplib
import ssl
from datetime import datetime, timezone
from ftplib import FTP_TLS
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Optional

from core.db.queries import have_already_exported_image, update_exported_at
from core.uploader.base import Uploader

if TYPE_CHECKING:
    from socket import socket

    from core.exports import ParquetExport

from loguru import logger


class ImplicitFtpTls(ftplib.FTP_TLS):
    """
    FTP_TLS subclass that automatically wraps sockets in SSL to support implicit FTPS.

    https://stackoverflow.com/questions/12164470/python-ftp-implicit-tls-connection-issue
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Create instance from parent class."""
        super().__init__(*args, **kwargs)
        self._sock: socket | None = None

    @property
    def sock(self) -> socket | None:
        """Return the socket."""
        return self._sock

    @sock.setter
    def sock(self, value: socket) -> None:
        """When modifying the socket, ensure that it is ssl wrapped."""
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value)
        self._sock = value


class FTPSUploader(Uploader):
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

    def upload_dicom_image(
        self,
        zip_content: BinaryIO,
        pseudo_anon_image_id: str,
        remote_directory: str,
    ) -> None:
        """Upload a DICOM image to the FTPS server."""
        logger.info("Starting FTPS upload of '{}'", pseudo_anon_image_id)

        # name destination to {project-slug}/{study-pseudonymised-id}.zip
        if have_already_exported_image(pseudo_anon_image_id):
            msg = "Image already exported"
            raise RuntimeError(msg)

        # Create the remote directory if it doesn't exist
        ftp = _connect_to_ftp(self.host, self.port, self.user, self.password)
        _create_and_set_as_cwd(ftp, remote_directory)
        command = f"STOR {pseudo_anon_image_id}.zip"
        logger.debug("Running {}", command)

        # Store the file using a binary handler
        try:
            ftp.storbinary(command, zip_content)
        except ftplib.all_errors as ftp_error:
            ftp.quit()
            error_msg = "Failed to run STOR command '{}': '{}'"
            raise ConnectionError(error_msg, command, ftp_error) from ftp_error

        # Close the FTP connection
        ftp.quit()

        # Update the exported_at timestamp in the PIXL database
        update_exported_at(pseudo_anon_image_id, datetime.now(tz=timezone.utc))
        logger.info("Finished FTPS upload of '{}'", pseudo_anon_image_id)

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
        logger.info("Starting FTPS upload of files for '{}'", parquet_export.project_slug)

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
        logger.info("Finished FTPS upload of files for '{}'", parquet_export.project_slug)


def _connect_to_ftp(ftp_host: str, ftp_port: int, ftp_user: str, ftp_password: str) -> FTP_TLS:
    # Connect to the server and login
    try:
        ftp = ImplicitFtpTls()
        ftp.connect(ftp_host, int(ftp_port))
        ftp.login(ftp_user, ftp_password)
        ftp.prot_p()
    except ftplib.all_errors as ftp_error:
        error_msg = "Failed to connect to FTPS server"
        raise ConnectionError(error_msg, ftp_error) from ftp_error
    return ftp


def _create_and_set_as_cwd_multi_path(ftp: FTP_TLS, remote_multi_dir: Path) -> None:
    """Create (and cwd into) a multi dir path, analogously to mkdir -p"""
    if remote_multi_dir.is_absolute():
        # would require some special handling and we don't need it
        err = "must be relative path"
        raise ValueError(err)
    logger.info("_create_and_set_as_cwd_multi_path {}", remote_multi_dir)
    # path should be pretty normalised, so assume split is safe
    sub_dirs = str(remote_multi_dir).split("/")
    for sd in sub_dirs:
        _create_and_set_as_cwd(ftp, sd)


def _create_and_set_as_cwd(ftp: FTP_TLS, project_dir: str) -> None:
    try:
        ftp.cwd(project_dir)
        logger.debug("'{}' exists on remote ftp, so moving into it", project_dir)
    except ftplib.error_perm:
        logger.info("creating '{}' on remote ftp and moving into it", project_dir)
        # Directory doesn't exist, so create it
        ftp.mkd(project_dir)
        ftp.cwd(project_dir)
