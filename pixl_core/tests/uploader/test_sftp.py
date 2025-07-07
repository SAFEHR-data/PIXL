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
import shutil
import tempfile
import time
from collections.abc import Generator
from pathlib import Path
from typing import Optional

import docker
import paramiko
import pytest
from core.uploader._sftp import SFTPUploader
from decouple import config

TEST_DIR = Path(__file__).parents[1]

os.environ["SFTP_HOST"] = "localhost"
os.environ["SFTP_USERNAME"] = "testuser"
os.environ["SFTP_PASSWORD"] = "testpass"
os.environ["SFTP_PORT"] = "2222"


class MockSFTPUploader(SFTPUploader):
    """Mock SFTPUploader for testing."""

    def __init__(self) -> None:
        """Initialise the mock uploader with hardcoded values for SFTP config."""
        self.host = os.environ["SFTP_HOST"]
        self.user = os.environ["SFTP_USERNAME"]
        self.password = os.environ["SFTP_PASSWORD"]
        self.port = int(os.environ["SFTP_PORT"])
        self.project_slug = "test-project"

    def _set_config(self) -> None:
        """Override to avoid Azure Key Vault dependency in tests."""


class PixlSFTPServer:
    """Docker-based SFTP server for testing"""

    def __init__(self) -> None:
        """Initialize the DockerSFTPServer"""
        self.username = config("SFTP_USERNAME", default="testuser")
        self.password = config("SFTP_PASSWORD", default="testpass")
        self.port = int(config("SFTP_PORT", default=2222))
        self.docker_client: docker.DockerClient = docker.from_env()
        self.container: Optional[docker.models.containers.Container] = None
        self.upload_dir: Optional[Path] = None

    def start(self) -> dict:
        """Start the SFTP server container"""
        temp_dir = tempfile.mkdtemp()

        # Create users.conf for the SFTP server
        users_conf = f"{self.username}:{self.password}:1001:1001:upload"
        users_conf_path = Path(temp_dir) / "users.conf"
        users_conf_path.write_text(users_conf)

        self.upload_dir = Path(temp_dir) / "upload"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        # Start container
        self.container = self.docker_client.containers.run(
            "atmoz/sftp:alpine",
            command=f"{self.username}:{self.password}:::upload",
            ports={"22/tcp": self.port},
            volumes={str(self.upload_dir): {"bind": f"/home/{self.username}/upload", "mode": "rw"}},
            detach=True,
            remove=True,
        )

        # Wait for container to be ready
        self._wait_for_server()

        return {
            "host": "localhost",
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "upload_dir": self.upload_dir,
        }

    def _wait_for_server(self, timeout: int = 30) -> None:
        """Wait for SFTP server to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # noqa: S507
                ssh.connect(
                    "localhost",
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=5,
                )
                sftp = ssh.open_sftp()
                sftp.close()
                ssh.close()
            except (paramiko.SSHException, OSError, ConnectionError):
                time.sleep(1)
            else:
                return  # Connection successful

        err_str = f"SFTP server did not start within {timeout} seconds"
        raise TimeoutError(err_str)

    def stop(self) -> None:
        """Stop the SFTP server container"""
        if self.container:
            self.container.stop()
            self.container = None

        if self.upload_dir:
            shutil.rmtree(self.upload_dir, ignore_errors=True)
            self.upload_dir = None

    def is_running(self) -> bool:
        """Check if the SFTP server is running"""
        if not self.container:
            return False
        try:
            self.container.reload()
        except docker.errors.NotFound:
            return False
        else:
            return self.container.status == "running"


@pytest.fixture(scope="session")
def sftp_server() -> Generator[PixlSFTPServer, None, None]:
    """Return a running SFTP server container."""
    server = PixlSFTPServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture()
def sftp_uploader() -> MockSFTPUploader:
    """Return a MockSFTPUploader object."""
    return MockSFTPUploader()


@pytest.fixture()
def zip_content() -> Generator:
    """Directory containing the test data for uploading to the sftp server."""
    test_zip_file = TEST_DIR / "data" / "public.zip"
    with test_zip_file.open("rb") as file_content:
        yield file_content


def test_sftp_server_can_connect(sftp_server: PixlSFTPServer) -> None:
    """Tests that the SFTP server can be connected to."""
    assert sftp_server.is_running()
