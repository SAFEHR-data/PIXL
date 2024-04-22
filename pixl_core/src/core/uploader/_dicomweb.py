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

"""Uploader subclass for FTPS uploads."""

from __future__ import annotations

import json
from typing import Optional

import requests
from decouple import config  # type: ignore [import-untyped]
from loguru import logger

from core.uploader.base import Uploader


class DicomWebUploader(Uploader):
    """Upload strategy for a DicomWeb server."""

    def __init__(self, project_slug: str, keyvault_alias: Optional[str]) -> None:
        """Create instance of parent class"""
        super().__init__(project_slug, keyvault_alias)

    def _set_config(self) -> None:
        # Use the Azure KV alias as prefix if it exists, otherwise use the project name
        az_prefix = self.keyvault_alias
        az_prefix = az_prefix if az_prefix else self.project_slug

        self.user = self.keyvault.fetch_secret(f"{az_prefix}--dicomweb--username")
        self.password = self.keyvault.fetch_secret(f"{az_prefix}--dicomweb--password")
        self.orthanc_url = config("ORTHANC_URL")
        self.endpoint_name = self.keyvault.fetch_secret(f"{az_prefix}--dicomweb--url")
        self.url = self.orthanc_url + "/dicom-web/servers/" + self.endpoint_name

    def upload_dicom_image(self) -> None:
        msg = "Currently not implemented. Use `send_via_stow()` instead."
        raise NotImplementedError(msg)

    def send_via_stow(self, resource_id: str) -> None:
        """Upload a Dicom resource to the DicomWeb server from within Orthanc."""
        if not self._check_dicomweb_server():
            logger.info("Creating new DICOMWeb credentials")
            self._setup_dicomweb_credentials()

        headers = {"content-type": "application/json"}
        payload = {"Resources": [resource_id], "Synchronous": False}

        try:
            requests.post(
                self.url + "/stow",
                auth=(self.user, self.password),
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )
        except requests.exceptions.RequestException:
            logger.error("Failed to send via stow")
            raise
        else:
            logger.info("Dicom resource {} sent via stow", resource_id)

    def _check_dicomweb_server(self) -> bool:
        """Checks if the dicomweb server exists."""
        response = requests.get(self.url, auth=(self.user, self.password), timeout=30)
        success_code = 200
        if response.status_code != success_code:
            return False
        return True

    def _setup_dicomweb_credentials(self) -> None:
        """Add the necessary credentials to the DicomWeb server in Orthanc."""
        AZ_DICOM_ENDPOINT_URL = config("AZ_DICOM_ENDPOINT_URL")
        HTTP_TIMEOUT = int(config("HTTP_TIMEOUT", default=30))

        dicomweb_config = {
            "Url": AZ_DICOM_ENDPOINT_URL,
            "HttpHeaders": {
                "Authorization": f"{self.user}:{self.password}",
            },
            "HasDelete": True,
            "Timeout": HTTP_TIMEOUT,
        }

        headers = {"content-type": "application/json"}
        try:
            requests.put(
                self.url,
                auth=(self.user, self.password),
                headers=headers,
                data=json.dumps(dicomweb_config),
                timeout=10,
            )
        except requests.exceptions.RequestException:
            logger.error("Failed to update DICOMweb token")
            raise
        else:
            logger.info("DICOMweb token updated")

    def upload_parquet_files(self) -> None:
        msg = "DICOMWeb uploader does not support parquet files"
        raise NotImplementedError(msg)
