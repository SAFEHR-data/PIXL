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
    from pathlib import Path
    from socket import socket

from core._database import get_project_slug_from_db, update_exported_at_and_save

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


def upload_dicom_image(local_file_path: Path, pseudo_anon_id: str) -> None:
    """Top level way to upload an image."""
    # Create the remote directory if it doesn't exist
    # rename destination to {project-slug}/{study-pseduonymised-id}.zip
    remote_directory = get_project_slug_from_db(pseudo_anon_id)

    # Store the file using a binary handler
    with local_file_path.open("rb") as file_content:
        upload_content(
            # wrong directory name, can get that from the image at least
            file_content,
            remote_dir=remote_directory,
            remote_file=f"{pseudo_anon_id}.zip",
        )

    update_exported_at_and_save(pseudo_anon_id, datetime.now(tz=timezone.utc))


def upload_content(content: BinaryIO, *, remote_dir: str, remote_file: str) -> str:
    """Upload local file to directory in ftp server."""
    ftp = _connect_to_ftp()

    _create_and_set_as_cwd(ftp, remote_dir)

    # Store the file using a binary handler
    command = f"STOR {remote_file}"
    logger.debug("Running %s", command)
    ftp.storbinary(command, content)

    # Close the FTP connection
    ftp.quit()
    logger.debug("Finished uploading!")
    return f"{remote_dir}/{remote_file}"


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
