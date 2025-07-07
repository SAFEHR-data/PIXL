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

"""Uploader subclass for SFTP."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import BinaryIO, Optional

import paramiko
from loguru import logger

from core.exports import ParquetExport
from core.uploader._orthanc import StudyTags, get_study_zip_archive
from core.uploader.base import Uploader


class SFTPUploader(Uploader):
    """Upload strategy for an SFTP server."""

    def __init__(self, project_slug: str, keyvault_alias: Optional[str]) -> None:
        """Create instance of parent class"""
        super().__init__(project_slug, keyvault_alias)

    def _set_config(self) -> None:
        """Set the configuration for the SFTP uploader."""
        # Use the Azure KV alias as prefix if it exists, otherwise use the project name
        az_prefix = self.keyvault_alias
        az_prefix = az_prefix if az_prefix else self.project_slug

        # Get SFTP connection details from keyvault
        self.host = self.keyvault.fetch_secret(f"{az_prefix}--sftp--host")
        self.username = self.keyvault.fetch_secret(f"{az_prefix}--sftp--username")
        self.password = self.keyvault.fetch_secret(f"{az_prefix}--sftp--password")
        self.port = int(self.keyvault.fetch_secret(f"{az_prefix}--sftp--port"))
        self.known_hosts_path = self.keyvault.fetch_secret(f"{az_prefix}--sftp--known-hosts-path")

    def _upload_dicom_image(self, study_id: str, study_tags: StudyTags) -> None:
        """
        Upload DICOM image via SFTP.

        :param study_id: Orthanc Study ID
        :param study_tags: Study tags containing metadata
        """
        # Get DICOM zip archive from Orthanc
        zip_content = get_study_zip_archive(study_id)
        self.send_via_sftp(
            zip_content,
            study_tags.pseudo_anon_image_id,
            remote_directory=self.project_slug,
        )

    def send_via_sftp(
        self, zip_content: BinaryIO, pseudo_anon_image_id: str, remote_directory: str
    ) -> None:
        """Send the zip content to the SFTP server."""
        filename = f"{pseudo_anon_image_id}.zip"

        with self._connect_client() as sftp_client:
            _sftp_create_remote_directory(sftp_client, remote_directory)
            sftp_client.chdir(remote_directory)
            sftp_client.putfo(zip_content, filename)

    def upload_parquet_files(self, parquet_export: ParquetExport, remote_directory: str) -> None:
        """
        Upload parquet to FTPS under <project name>/<extract datetime>/parquet.
        :param parquet_export: instance of the ParquetExport class
        The final directory structure will look like this:
        <project-slug>
        ├── <extract_datetime_slug>
        │   └── parquet
        │       ├── omop
        │       │   └── public
        │       │       └── PROCEDURE_OCCURRENCE.parquet
        │       └── radiology
        │           └── IMAGE_LINKER.parquet
        ├── <pseudonymised_ID_DICOM_dataset_1>.zip
        └── <pseudonymised_ID_DICOM_dataset_2>.zip
        ...
        """
        logger.info("Starting SFTP upload of files for '{}'", parquet_export.project_slug)

        source_root_dir = parquet_export.current_extract_base
        source_files = [f for f in source_root_dir.rglob("*.parquet") if f.is_file()]
        if not source_files:
            msg = f"No files found in {source_root_dir}"
            raise FileNotFoundError(msg)

        parquet_dir = f"{parquet_export.project_slug}/{parquet_export.extract_time_slug}/parquet"
        upload_dir = f"{remote_directory}/{parquet_dir}"
        with self._connect_client() as sftp_client:
            _sftp_create_remote_directory(sftp_client, upload_dir)
            for source_path in source_files:
                sftp_client.chdir(None)  # reset
                sftp_client.chdir(upload_dir)

                source_rel_path = source_path.relative_to(source_root_dir)
                source_rel_dir = source_rel_path.parent
                source_filename_only = source_rel_path.relative_to(source_rel_dir)
                _sftp_create_remote_directory(sftp_client, str(source_rel_dir))
                sftp_client.chdir(str(source_rel_dir))
                sftp_client.put(source_path, str(source_filename_only))

        logger.info("Finished SFTP upload of files for '{}'", parquet_export.project_slug)

    @contextmanager
    def _connect_client(self) -> Generator[paramiko.SFTPClient, None, None]:
        """Connect to the SFTP client as a context manager"""
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())
        ssh_client.load_host_keys(self.known_hosts_path)
        ssh_client.connect(
            self.host, port=self.port, username=self.username, password=self.password
        )
        sftp_client = ssh_client.open_sftp()
        try:
            yield sftp_client
        finally:
            sftp_client.close()
            ssh_client.close()


def _sftp_create_remote_directory(sftp_client: paramiko.SFTPClient, directory: str) -> None:
    """
    Create remote directory and its parents if it doesn't exist.

    :param sftp_client: SFTP client instance
    :param directory: Directory path to create
    """
    try:
        sftp_client.stat(directory)
    except FileNotFoundError:
        parent_dir = os.path.dirname(directory)  # noqa: PTH120
        _sftp_create_remote_directory(sftp_client, str(parent_dir))
        sftp_client.mkdir(directory)
        logger.debug(f"Created remote directory: {directory}")
