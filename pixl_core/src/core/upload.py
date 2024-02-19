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
"""Functionality to upload files to an endpoint."""

from __future__ import annotations

import ftplib
import logging
import ssl
from datetime import datetime, timezone
from ftplib import FTP_TLS
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO

from decouple import config

if TYPE_CHECKING:
    from socket import socket

    from core.exports import ParquetExport


from core.db.queries import get_project_slug_from_db, update_exported_at

logger = logging.getLogger(__name__)


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


def upload_dicom_image(zip_content: BinaryIO, pseudo_anon_id: str) -> None:
    """Top level way to upload an image."""
    logger.info("Starting FTPS upload of '%s'", pseudo_anon_id)

    # rename destination to {project-slug}/{study-pseduonymised-id}.zip
    remote_directory = get_project_slug_from_db(pseudo_anon_id)

    # Create the remote directory if it doesn't exist
    ftp = _connect_to_ftp()
    _create_and_set_as_cwd(ftp, remote_directory)
    command = f"STOR {pseudo_anon_id}.zip"
    logger.debug("Running %s", command)

    # Store the file using a binary handler
    try:
        logger.info("Running command %s", command)
        ftp.storbinary(command, zip_content)
    except ftplib.all_errors as ftp_error:
        ftp.quit()
        error_msg = f"Failed to run STOR command : {command}"
        raise ConnectionError(error_msg, command, ftp_error) from ftp_error

    # Close the FTP connection
    ftp.quit()

    update_exported_at(pseudo_anon_id, datetime.now(tz=timezone.utc))
    logger.info("Finished FTPS upload of '%s'", pseudo_anon_id)


def upload_parquet_files(parquet_export: ParquetExport) -> None:
    """Upload parquet to FTPS under <project name>/<extract datetime>/parquet."""
    logger.info("Starting FTPS upload of files for '%s'", parquet_export.project_slug)

    source_root_dir = parquet_export.current_extract_base
    # Create the remote directory if it doesn't exist
    ftp = _connect_to_ftp()
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


def _connect_to_ftp() -> FTP_TLS:
    # Set your FTP server details
    ftp_host = config("FTP_HOST")
    ftp_port = config("FTP_PORT")  # FTPS usually uses port 21
    ftp_user = config("FTP_USER_NAME")
    ftp_password = config("FTP_USER_PASSWORD")

    # Connect to the server and login
    try:
        ftp = ImplicitFtpTls()
        ftp.connect(ftp_host, int(ftp_port))
        ftp.set_debuglevel(2)
        ftp.login(ftp_user, ftp_password)
        ftp.prot_p()
    except ftplib.all_errors as ftp_error:
        error_msg = f"Failed to connect to FTPS server: {ftp_user}@{ftp_host}:{ftp_port}"
        raise ConnectionError(error_msg) from ftp_error
    return ftp


def _create_and_set_as_cwd_multi_path(ftp: FTP_TLS, remote_multi_dir: Path) -> None:
    """Create (and cwd into) a multi dir path, analogously to mkdir -p"""
    if remote_multi_dir.is_absolute():
        # would require some special handling and we don't need it
        err = "must be relative path"
        raise ValueError(err)
    logger.info("_create_and_set_as_cwd_multi_path %s", remote_multi_dir)
    # path should be pretty normalised, so assume split is safe
    sub_dirs = str(remote_multi_dir).split("/")
    for sd in sub_dirs:
        _create_and_set_as_cwd(ftp, sd)


def _create_and_set_as_cwd(ftp: FTP_TLS, project_dir: str) -> None:
    try:
        ftp.cwd(project_dir)
        logger.debug("'%s' exists on remote ftp, so moving into it", project_dir)
    except ftplib.error_perm:
        logger.info("creating '%s' on remote ftp and moving into it", project_dir)
        # Directory doesn't exist, so create it
        ftp.mkd(project_dir)
        ftp.cwd(project_dir)
