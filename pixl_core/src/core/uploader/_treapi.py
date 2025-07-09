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

import zipfile
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from core.uploader._orthanc import StudyTags
from core.uploader.base import Uploader

from ._orthanc import get_study_zip_archive

if TYPE_CHECKING:
    from core.exports import ParquetExport

TRE_API_URL = "https://api.tre.arc.ucl.ac.uk/v0"
HTTP_OK = 200
HTTP_CREATED = 201


class TreApiUploader(Uploader):
    """Uploader subclass for the ARC TRE API."""

    def __init__(self, project_slug: str, keyvault_alias: str | None) -> None:
        """Initialize the TreApiUploader with the given configuration."""
        super().__init__(project_slug, keyvault_alias)
        self.host = TRE_API_URL

    def _set_config(self) -> None:
        # Use the Azure KV alias as prefix if it exists, otherwise use the project name
        az_prefix = self.keyvault_alias
        az_prefix = az_prefix if az_prefix else self.project_slug
        self.token = self.keyvault.fetch_secret(f"{az_prefix}--ftp--token")  # TRE API token
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def _upload_dicom_image(
        self,
        study_id: str,
        study_tags: StudyTags,
    ) -> None:
        """Upload a DICOM image to the TRE API."""
        zip_content = get_study_zip_archive(study_id)
        self.send_via_api(zip_content, study_tags.pseudo_anon_image_id)
        self.flush()  # Not ideal, as this may cause multiple flushes in short period

    def upload_parquet_files(self, parquet_export: "ParquetExport") -> None:
        """Upload parquet files as a zip archive to the ARC TRE API."""
        # Zip the files
        source_root_dir = parquet_export.current_extract_base
        source_files = [x for x in source_root_dir.rglob("*.parquet") if x.is_file()]
        if not source_files:
            msg = f"No files found in {source_root_dir}"
            raise FileNotFoundError(msg)
        zip_file = _zip_files(source_files, f"{parquet_export.current_extract_base}.zip")

        # Upload the zip file
        self.send_via_api(BytesIO(zip_file.read_bytes()), zip_file.name)
        self.flush()  # Not ideal, as this may cause multiple flushes in short period

    def send_via_api(self, data: BytesIO, filename: str) -> None:
        """Upload data to the ARC TRE API."""
        if self._token_info_status() != HTTP_OK:
            msg = f"Token invalid: {self.token}"
            raise RuntimeError(msg)

        self._upload_file(data, filename)

    def _token_info_status(self) -> int:
        """Get the status of the token."""
        response = requests.get(url=f"{self.host}/tokens/info", headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.status_code

    def _upload_file(self, content: BytesIO, filename: str) -> None:
        """Upload a file into the TRE airlock."""
        response = requests.post(
            url=f"{self.host}/airlock/upload/{filename}",
            headers=self.headers,
            data=content,
            timeout=10,
        )
        response.raise_for_status()
        if response.status_code != HTTP_CREATED:
            msg = f"Failed to upload file. Response: {response}"
            raise RuntimeError(msg)

    def flush(self) -> None:
        """
        Flush the TRE airlock to move files into the main project storage.
        Calling flush scans and moves the files in quarantine storage into
        the associated project storage. This happens asynchronously
        This is an *expensive* operation so please call with a delay suitable
        for your project e.g. once per day.
        NOTE: Files will be deleted if they aren't moved within 7 days
        """
        response = requests.put(f"{self.host}/airlock/flush", headers=self.headers, timeout=10)
        response.raise_for_status()
        if response.status_code != HTTP_CREATED:
            msg = f"Failed to flush. Response: {response}"
            raise RuntimeError(msg)


def _zip_files(files: list[Path], zip_filename: str) -> Path:
    """Create a zip file from a list of files."""
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            zipf.write(file, arcname=file.name)
    return Path(zip_filename)
