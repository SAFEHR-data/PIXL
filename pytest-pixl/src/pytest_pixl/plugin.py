"""Pytest fixtures."""

import os
import threading
from collections.abc import Generator

import pytest

from pytest_pixl.ftpserver import PixlFTPServer


@pytest.fixture(scope="module")
def ftps_server(tmp_path_factory) -> Generator[PixlFTPServer, None, None]:
    """
    Spins up an FTPS server in a separate process for testing. Configuration is controlled by the
    FTP_* environment variables.
    """
    tmp_home_dir = tmp_path_factory.mktemp("ftps_server") / os.environ["FTP_USER_NAME"]
    tmp_home_dir.mkdir()
    ftps_server = PixlFTPServer(home_dir=str(tmp_home_dir))
    thread = threading.Thread(target=ftps_server.server.serve_forever)
    thread.start()
    yield ftps_server
    ftps_server.server.close_all()
