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
"""Pytest fixtures."""
import sys
import threading
from collections.abc import Generator
from enum import Enum

import pytest

from pytest_pixl.ftpserver import PixlFTPServer


class FtpHostAddress(Enum):
    """
    Docker on Linux is such that if we bind the FTP server to localhost, traffic from container
    to host can't get through. Instead you must bind to the docker host interface.

    However, some tests initiate FTP connections from pytest (running on host) rather than
    containers. These require the server to be bound to localhost. So the test itself needs
    to tell us where to bind (using a fixture called ftp_host_address)

    Binding to all interfaces (0.0.0.0) would work, but is not ideal as you're opening up
    the test FTP server to any passersby.

    On macOS, you can just bind to localhost and traffic from containers or localhost gets through.
    Haven't tested Windows, am assuming the macOS way works.
    """

    LOCALHOST = 1
    DOCKERHOST = 2

    def to_host_ip_address(self):
        """Convert the test's requirement into a platform-dependent host IP address"""
        if self == FtpHostAddress.DOCKERHOST and sys.platform == "linux":
            return "172.17.0.1"
        return "127.0.0.1"


@pytest.fixture(scope="session")
def ftps_server(
    tmp_path_factory, ftp_host_address: FtpHostAddress
) -> Generator[PixlFTPServer, None, None]:
    """
    Spins up an FTPS server in a separate process for testing. Configuration is controlled by the
    FTP_* environment variables.
    """
    tmp_home_dir_root = tmp_path_factory.mktemp("ftps_server")
    ftps_server = PixlFTPServer(
        home_root=tmp_home_dir_root, host_address=ftp_host_address.to_host_ip_address()
    )
    thread = threading.Thread(target=ftps_server.server.serve_forever)
    thread.start()
    yield ftps_server
    ftps_server.server.close_all()
