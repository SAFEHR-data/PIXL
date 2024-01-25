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
import os
import ssl
from datetime import datetime, timezone
from ftplib import FTP_TLS
from typing import TYPE_CHECKING, Any, BinaryIO

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
    # rename destination to {project-slug}/{study-pseduonymised-id}.zip
    remote_directory = get_project_slug_from_db(pseudo_anon_id)

    # Create the remote directory if it doesn't exist
    ftp = _connect_to_ftp()
    _create_and_set_as_cwd(ftp, remote_directory)
    command = f"STOR {pseudo_anon_id}.zip"
    logger.debug("Running %s", command)

    # Store the file using a binary handler
    ftp.storbinary(command, zip_content)

    # Close the FTP connection
    ftp.quit()
    logger.debug("Finished uploading!")

    update_exported_at(pseudo_anon_id, datetime.now(tz=timezone.utc))


def upload_radiology_reports(pe: ParquetExport) -> None:
    """Top level way to upload an image."""
    latest_dir = pe.latest_parent_dir
    # Create the remote directory if it doesn't exist
    ftp = _connect_to_ftp()
    _create_and_set_as_cwd(ftp, pe.project_slug)
    for path in latest_dir.rglob("**"):
        print(path)
    _create_and_set_as_cwd_parquet(ftp, project_slug, list_dir)

    # loop through files here?
    command = f"STOR {public_dir}.parquet"
    zip_content = data
    logger.debug("Running %s", command)

    # Store the file using a binary handler
    ftp.storbinary(command, zip_content)

    # Close the FTP connection
    ftp.quit()
    logger.debug("Finished uploading!")

    # update_exported_at(pseudo_anon_id, datetime.now(tz=timezone.utc))


def _connect_to_ftp() -> FTP_TLS:
    # Set your FTP server details
    ftp_host = os.environ["FTP_HOST"]
    ftp_port = os.environ["FTP_PORT"]  # FTPS usually uses port 21
    ftp_user = os.environ["FTP_USER_NAME"]
    ftp_password = os.environ["FTP_USER_PASS"]

    # Connect to the server and login
    ftp = ImplicitFtpTls()
    ftp.connect(ftp_host, int(ftp_port))
    ftp.login(ftp_user, ftp_password)
    ftp.prot_p()
    return ftp


def _create_and_set_as_cwd(ftp: FTP_TLS, project_dir: str) -> None:
    try:
        ftp.cwd(project_dir)
        logger.info("'%s' exists on remote ftp, so moving into it", project_dir)
    except ftplib.error_perm:
        logger.info("creating '%s' on remote ftp and moving into it", project_dir)
        # Directory doesn't exist, so create it
        ftp.mkd(project_dir)
        ftp.cwd(project_dir)


def _create_and_set_as_cwd_parquet(ftp: FTP_TLS, list_dir: list) -> None:
    for dir_current in list_dir:
        try:
            ftp.cwd(dir_current)
            logger.info("'%s' exists on remote ftp, so moving into it", dir_current)
        except ftplib.error_perm:
            logger.info("creating '%s' on remote ftp and moving into it", dir_current)
            # Directory doesn't exist, so create it
            ftp.mkd(dir_current)
            ftp.cwd(dir_current)
