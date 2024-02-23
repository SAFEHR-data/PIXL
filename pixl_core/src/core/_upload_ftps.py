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

"""Helper functions for setting up a connection to an FTPS server."""

from __future__ import annotations

import ftplib
import logging
import ssl
from ftplib import FTP_TLS
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path
    from socket import socket

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


def _connect_to_ftp(ftp_host: str, ftp_port: int, ftp_user: str, ftp_password: str) -> FTP_TLS:
    # Connect to the server and login
    try:
        ftp = ImplicitFtpTls()
        ftp.connect(ftp_host, int(ftp_port))
        ftp.login(ftp_user, ftp_password)
        ftp.prot_p()
    except ftplib.all_errors as ftp_error:
        error_msg = "Failed to connect to FTPS server: '%s'"
        raise ConnectionError(error_msg, ftp_error) from ftp_error
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
