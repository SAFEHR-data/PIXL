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

"""Uploader subclass for DICOMweb uploads."""

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
        self.az_prefix = az_prefix if az_prefix else self.project_slug

        self.orthanc_user = config("ORTHANC_USERNAME")
        self.orthanc_password = config("ORTHANC_PASSWORD")
        self.orthanc_url = config("ORTHANC_URL")
        self.endpoint_user = self.keyvault.fetch_secret(f"{self.az_prefix}--dicomweb--username")
        self.endpoint_password = self.keyvault.fetch_secret(f"{self.az_prefix}--dicomweb--password")
        self.endpoint_url = self.keyvault.fetch_secret(f"{self.az_prefix}--dicomweb--url")
        self.orthanc_dicomweb_url = self.orthanc_url + "/dicom-web/servers/" + self.az_prefix

    def upload_dicom_image(self) -> None:
        msg = "Currently not implemented. Use `send_via_stow()` instead."
        raise NotImplementedError(msg)

    def send_via_stow(self, resource_id: str) -> requests.Response:
        """Upload a Dicom resource to the DicomWeb server from within Orthanc."""
        if not self._check_dicomweb_server():
            logger.info("Creating new DICOMWeb credentials")
            self._setup_dicomweb_credentials()

        headers = {"content-type": "application/dicom", "accept": "application/dicom+json"}
        payload = {"Resources": [resource_id], "Synchronous": False}

        try:
            response = requests.post(
                self.orthanc_dicomweb_url + "/stow",
                auth=(self.orthanc_user, self.orthanc_password),
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            logger.error("Failed to send via stow")
            raise
        else:
            logger.info("Dicom resource {} sent via stow", resource_id)
        return response

    def _check_dicomweb_server(self) -> bool:
        """Checks if the dicomweb server exists."""
        response = requests.get(
            self.orthanc_dicomweb_url, auth=(self.orthanc_user, self.orthanc_password), timeout=30
        )
        success_code = 200
        if response.status_code != success_code:
            return False
        return True

    def _setup_dicomweb_credentials(self) -> None:
        """
        Add the necessary credentials to the DicomWeb server in Orthanc.
        This dyniamically creates a new endpoint in Orthanc with the necessary credentials, so we
        can avoid hardcoding the credentials in the Orthanc configuration at build time.
        """
        HTTP_TIMEOUT = int(config("HTTP_TIMEOUT", default=30))

        dicomweb_config = {
            "Url": self.endpoint_url,
            "Username": self.endpoint_user,
            "Password": self.endpoint_password,
            "HasDelete": True,
            "Timeout": HTTP_TIMEOUT,
        }

        headers = {"content-type": "application/json"}
        try:
            requests.put(
                self.orthanc_dicomweb_url,
                auth=(self.orthanc_user, self.orthanc_password),
                headers=headers,
                data=json.dumps(dicomweb_config),
                timeout=10,
            )
        except requests.exceptions.RequestException:
            logger.error("Failed to update DICOMweb config for {}", self.orthanc_dicomweb_url)
            raise
        else:
            logger.info("Set up DICOMweb config for {}", self.orthanc_dicomweb_url)

    def upload_parquet_files(self) -> None:
        msg = "DICOMWeb uploader does not support parquet files"
        raise NotImplementedError(msg)
