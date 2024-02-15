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

import threading
from collections.abc import Generator

import pytest

from pytest_pixl.ftpserver import PixlFTPServer


@pytest.fixture(scope="session")
def ftps_server(tmp_path_factory) -> Generator[PixlFTPServer, None, None]:
    """
    Spins up an FTPS server in a separate process for testing. Configuration is controlled by the
    FTP_* environment variables.
    """
    tmp_home_dir_root = tmp_path_factory.mktemp("ftps_server")
    ftps_server = PixlFTPServer(home_root=tmp_home_dir_root)
    thread = threading.Thread(target=ftps_server.server.serve_forever)
    thread.start()
    yield ftps_server
    ftps_server.server.close_all()
