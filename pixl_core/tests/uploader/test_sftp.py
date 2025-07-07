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
"""Test uploading files to an SFTP endpoint."""

import os
from collections.abc import Generator
from pathlib import Path

import paramiko
import pytest
from core.uploader._sftp import SFTPUploader
from pixl_core.tests.uploader.helpers.sftpserver import SFTPServer

TEST_DIR = Path(__file__).parents[1]

os.environ["SFTP_HOST"] = "localhost"
os.environ["SFTP_USERNAME"] = "testuser"
os.environ["SFTP_PASSWORD"] = "testpass"
os.environ["SFTP_PORT"] = "2222"


class MockSFTPUploader(SFTPUploader):
    """Mock SFTPUploader for testing."""

    def __init__(self, host_key_path: Path) -> None:
        """Initialise the mock uploader with hardcoded values for SFTP config."""
        self.host = os.environ["SFTP_HOST"]
        self.user = os.environ["SFTP_USERNAME"]
        self.password = os.environ["SFTP_PASSWORD"]
        self.port = int(os.environ["SFTP_PORT"])
        self.host_key_path = host_key_path
        self.project_slug = "test-project"

    def _set_config(self) -> None:
        """Override to avoid Azure Key Vault dependency in tests."""


@pytest.fixture(scope="module")
def host_keys(tmp_path_factory) -> Path:
    """Creates temporary directory for host keys (will be populated by server)"""
    return tmp_path_factory.mktemp("host_keys")


@pytest.fixture(scope="module")
def sftp_server(host_keys) -> Generator[SFTPServer, None, None]:
    """Return a running SFTP server container."""
    server = SFTPServer(host_keys)
    server.start()
    yield server
    server.stop()


@pytest.fixture()
def sftp_uploader(host_keys) -> MockSFTPUploader:
    """Return a MockSFTPUploader object."""
    return MockSFTPUploader(host_keys)


@pytest.fixture()
def zip_content() -> Generator:
    """Directory containing the test data for uploading to the sftp server."""
    test_zip_file = TEST_DIR / "data" / "public.zip"
    with test_zip_file.open("rb") as file_content:
        yield file_content


def test_sftp_server_can_connect(sftp_server, sftp_uploader):
    """Tests that the SFTP server can be connected to."""
    assert sftp_server.is_running()

    # Test actual SFTP connection using the uploader
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())
    ssh_client.load_host_keys(str(sftp_uploader.host_key_path / "known_hosts"))

    try:
        ssh_client.connect(
            sftp_uploader.host,
            port=sftp_uploader.port,
            username=sftp_uploader.user,
            password=sftp_uploader.password,
            timeout=5,
        )
        sftp_client = ssh_client.open_sftp()
        sftp_client.close()
        ssh_client.close()
    except paramiko.SSHException as e:
        ssh_client.close()
        pytest.fail(f"Failed to connect to SFTP server: {e}")
