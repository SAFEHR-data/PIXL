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

"""Uploader subclass for the ARC TRE API."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from decouple import config

from core.uploader._orthanc import StudyTags, get_study_zip_archive
from core.uploader.base import Uploader

if TYPE_CHECKING:
    from core.exports import ParquetExport

# API Configuration
TRE_API_URL = "https://api.tre.arc.ucl.ac.uk/v0"
REQUEST_TIMEOUT = 10

# HTTP Status Codes
HTTP_OK = 200


class TreApiUploader(Uploader):
    """
    Uploader for the ARC TRE API.

    This uploader handles uploading DICOM images and parquet files to the ARC TRE
    via their REST API. Files are uploaded to an airlock and then flushed to the
    main project storage.
    """

    def __init__(self, project_slug: str, keyvault_alias: str | None = None) -> None:
        """
        Initialize the TRE API uploader.

        Args:
            project_slug: The project identifier
            keyvault_alias: Optional Azure Key Vault alias for authentication

        """
        super().__init__(project_slug, keyvault_alias)

    def _set_config(self) -> None:
        """Set up authentication configuration from Azure Key Vault."""
        # Use the Azure KV alias as prefix if it exists, otherwise use the project name
        prefix = self.keyvault_alias or self.project_slug
        self.token = self.keyvault.fetch_secret(f"{prefix}--api--token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.host = TRE_API_URL
        self.upload_timeout = int(config("HTTP_TIMEOUT", default=30))

    def _upload_dicom_image(self, study_id: str, study_tags: StudyTags) -> None:
        """
        Upload a DICOM image to the TRE API.

        Args:
            study_id: The study identifier
            study_tags: Study metadata containing the pseudo anonymized ID

        """
        zip_content = get_study_zip_archive(study_id)
        self.send_via_api(zip_content, study_tags.pseudo_anon_image_id)

    def upload_parquet_files(self, parquet_export: ParquetExport) -> None:
        """
        Upload parquet files as a zip archive to the TRE API.

        Args:
            parquet_export: The parquet export containing files to upload

        Raises:
            FileNotFoundError: If no parquet files are found in the export

        """
        source_root_dir = parquet_export.current_extract_base
        source_files = list(source_root_dir.rglob("*.parquet"))

        if not source_files:
            msg = f"No parquet files found in {source_root_dir}"
            raise FileNotFoundError(msg)

        # Create zip file
        zip_filename = f"{source_root_dir.name}.zip"
        zip_file = _create_zip_archive(source_files, source_root_dir, zip_filename)

        # Upload the zip file
        self.send_via_api(BytesIO(zip_file.read_bytes()), zip_file.name)
        self.flush()  # Not ideal, as this may cause multiple flushes in short period

    def send_via_api(self, data: BytesIO, filename: str) -> None:
        """
        Upload data to the TRE API.

        Args:
            data: The data to upload as a BytesIO stream
            filename: The filename for the uploaded data

        Raises:
            RuntimeError: If the token is invalid or upload fails

        """
        if not self._is_token_valid():
            msg = f"Token invalid: {self.token}"
            raise RuntimeError(msg)

        self._upload_file(data, filename)

    def _is_token_valid(self) -> bool:
        """
        Check if the current token is valid.

        Returns:
            True if the token is valid, False otherwise

        """
        try:
            response = requests.get(
                url=f"{self.host}/tokens/info",
                headers=self.headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException:
            return False
        else:
            return response.status_code == HTTP_OK

    def _upload_file(self, content: BytesIO, filename: str) -> None:
        """
        Upload a file to the TRE airlock.

        Args:
            content: The file content as a BytesIO stream
            filename: The filename for the uploaded file

        Raises:
            RuntimeError: If the upload fails

        """
        try:
            response = requests.post(
                url=f"{self.host}/airlock/upload/{filename}",
                headers=self.headers,
                data=content,
                timeout=self.upload_timeout,
            )
            response.raise_for_status()

        except requests.RequestException as e:
            msg = f"Failed to upload file {filename}: {e}"
            raise RuntimeError(msg) from e

    def flush(self) -> None:
        """
        Flush the TRE airlock to move files to main project storage.

        This operation scans and moves files from quarantine storage to the
        associated project storage. The operation is asynchronous and expensive,
        so it should be called sparingly (e.g., once per day).

        Note: Files are automatically deleted if not moved within 7 days.

        Raises:
            RuntimeError: If the flush operation fails

        """
        try:
            response = requests.put(
                url=f"{self.host}/airlock/flush",
                headers=self.headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

        except requests.RequestException as e:
            msg = f"Failed to flush airlock: {e}"
            raise RuntimeError(msg) from e


def _create_zip_archive(files: list[Path], root_dir: Path, zip_filename: str) -> Path:
    """
    Create a zip archive from a list of files.

    Args:
        files: List of file paths to include in the archive
        root_dir: Root directory for relative paths, used to preserve the
            directory structure of the input files
        zip_filename: Filename for the output zip file

    Returns:
        Path to the created zip file

    Raises:
        OSError: If zip file creation fails

    """
    zip_path = Path(zip_filename)

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                source_rel_path = file_path.relative_to(root_dir)
                zipf.write(file_path, arcname=source_rel_path)
    except OSError as e:
        msg = f"Failed to create zip file {zip_filename}: {e}"
        raise OSError(msg) from e

    return zip_path
