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

import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

import docker
import paramiko
from decouple import config
from loguru import logger


class SFTPServer:
    """SFTP server running in a Docker container for testing"""

    def __init__(self, host_key_path: Path) -> None:
        """Initialize the DockerSFTPServer"""
        self.username = config("SFTP_USERNAME", default="testuser")
        self.password = config("SFTP_PASSWORD", default="testpass")
        self.port = int(config("SFTP_PORT", default=2222))
        self.docker_client: docker.DockerClient = docker.from_env()
        self.host_key_path = host_key_path
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

        # Wait for container to be ready and extract host keys
        self._wait_for_server()
        self._extract_host_keys()

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
            except (paramiko.SSHException, OSError, ConnectionError, docker.errors.NotFound) as e:
                logger.info(f"Retrying SFTP connection: {e}")
                time.sleep(1)
            else:
                return  # Connection successful

        err_str = f"SFTP server did not start within {timeout} seconds"
        self.stop()
        raise TimeoutError(err_str)

    def _extract_host_keys(self) -> None:
        """Extract host keys from the running container"""
        if not self.container:
            msg = "Container not started"
            raise RuntimeError(msg)

        key_types = ["ssh_host_ed25519_key", "ssh_host_rsa_key", "ssh_host_ecdsa_key"]
        host_keys = []

        for key_type in key_types:
            exit_code, output = self.container.exec_run(f"cat /etc/ssh/{key_type}.pub")
            if exit_code == 0:
                host_key_content = output.decode().strip()
                logger.debug(f"Extracted {key_type}: {host_key_content}")
                host_keys.append(host_key_content)

        if not host_keys:
            msg = "No host keys found in container"
            raise RuntimeError(msg)

        # Create known_hosts file with all available keys
        known_hosts_path = self.host_key_path / "known_hosts"
        known_hosts_content = ""

        for host_key_content in host_keys:
            parts = host_key_content.split()
            if len(parts) >= 2:
                key_type = parts[0]  # e.g., "ssh-ed25519", "ssh-rsa"
                key_data = parts[1]  # base64 encoded key
                known_hosts_content += f"[localhost]:{self.port} {key_type} {key_data}\n"

        known_hosts_path.write_text(known_hosts_content)
        Path.chmod(known_hosts_path, 0o644)

        logger.debug(f"Created known_hosts file: {known_hosts_content}")

        # Also save the first public key for reference
        if host_keys:
            public_key_path = self.host_key_path / "ssh_host_key.pub"
            public_key_path.write_text(host_keys[0] + "\n")
            Path.chmod(public_key_path, 0o644)

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
