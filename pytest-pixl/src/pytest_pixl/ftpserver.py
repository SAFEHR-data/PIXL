#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
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
"""A ligthweight FTPS server supporting implicit SSL for use in PIXL tests."""

import importlib.resources
from pathlib import Path

from decouple import config
from loguru import logger
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import TLS_FTPHandler
from pyftpdlib.servers import ThreadedFTPServer

# User permission
# from https://pyftpdlib.readthedocs.io/en/latest/api.html#pyftpdlib.authorizers.DummyAuthorizer.add_user
# "e" = change directory (CWD, CDUP commands)
# "l" = list files (LIST, NLST, STAT, MLSD, MLST, SIZE commands)
# "r" = retrieve file from the server (RETR command)
# "a" = append data to an existing file (APPE command)
# "d" = delete file or directory (DELE, RMD commands)
# "f" = rename file or directory (RNFR, RNTO commands)
# "m" = create directory (MKD command)
# "w" = store a file to the server (STOR, STOU commands)
# "M" = change file mode / permission (SITE CHMOD command) New in 0.7.0
# "T" = change file modification time (SITE MFMT command) New in 1.5.3

USER_PERMISSIONS = "elradfmwMT"


class SSLImplicitFTPHandler(TLS_FTPHandler):
    """FTP handler class to support implicit SSL."""

    def handle(self) -> None:
        """Secure the connection with SSL."""
        self.secure_connection(self.ssl_context)

    def handle_ssl_established(self) -> None:
        """Handle the SSL established event."""
        TLS_FTPHandler.handle(self)

    def ftp_AUTH(self, arg: None) -> None:  # noqa: ARG002 Unused method argument
        """Handle the AUTH command."""
        self.respond("550 not supposed to be used with implicit SSL.")


class PixlFTPServer:
    """
    Mock FTPS server for PIXL tests. The server is configured to use SSL authentication.

    :param host: The hostname of the FTP server. Configurable with the 'FTP_HOST' environment
        variable, defaults to 'localhost'."
    :type host: str
    :param port: The port number of the FTP server. Configurable with the 'FTP_PORT' environment
        variable, defaults to 20021."
    :type port: int
    :param user_name: The username for the FTP server. Configurable with the 'FTP_USER_NAME'
        environment variable, defaults to 'pixl_user'."
    :type user_name: str
    :param user_password: The password for the FTP server. Configurable with the 'FTP_USER_PASSWORD'
        environment variable, defaults to 'longpassword'."
    :type user_password: str
    :param home_dir: The home directory for the FTP server. This is the directory where the
        user will be placed after login.
    :type home_dir: str
    """

    def __init__(self, home_root: Path, host_address: str) -> None:
        """
        Initialise the FTPS server. Sets the hostname, port, username and password
        from the corresponding environment variables.
        :param home_root: The directory where the user's home directory will be created.
        The home dir is the directory where the user will be placed after login.
        """
        self.host = host_address
        self.port = int(config("FTP_PORT", default=20021))

        self.user_name = config("FTP_USER_NAME", default="pixl_user")
        self.user_password = config("FTP_USER_PASSWORD", default="longpassword")
        self.home_dir: Path = home_root / self.user_name
        self.home_dir.mkdir()

        self.certfile = importlib.resources.files("pytest-pixl") / "src" / "resources" / "ssl" / "localhost.crt"
        self.keyfile = importlib.resources.files("pytest-pixl") / "src" / "resources" / "ssl" / "localhost.key"

        self.authorizer = DummyAuthorizer()
        self.handler = SSLImplicitFTPHandler

        self._add_user()
        self._setup_TLS_handler()
        self._create_server()

    def _add_user(self) -> None:
        """
        Add user to the FTP server and create its homedirectory. Note that the home directory
        will be a directory on the local filesystem!
        """
        self.authorizer.add_user(
            self.user_name, self.user_password, str(self.home_dir), perm=USER_PERMISSIONS
        )

    def _setup_TLS_handler(self) -> None:
        self._check_ssl_files()
        self.handler.certfile = self.certfile
        self.handler.keyfile = self.keyfile
        self.handler.authorizer = self.authorizer

    def _check_ssl_files(self) -> None:
        # Make sure we have access to the SSL certificates
        certfile_path = Path(self.certfile)
        keyfile_path = Path(self.keyfile)
        assert certfile_path.exists(), f"Could not find certfile at {certfile_path.absolute()}"
        assert keyfile_path.exists(), f"Could not find keyfile at {keyfile_path.absolute()}"

    def _create_server(self) -> ThreadedFTPServer:
        """
        Creates the FTPS server and returns it. The server can be started with the `serve_forever`
        method.
        """
        address = (self.host, self.port)
        logger.info("Starting FTP server on {}:{}", self.host, self.port)
        self.server = ThreadedFTPServer(address, self.handler)
        return self.server
