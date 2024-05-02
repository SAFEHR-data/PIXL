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
"""Test functionality to upload files to a DICOMWeb endpoint."""

from __future__ import annotations

import time

import pytest
import requests
from core.uploader._dicomweb import DicomWebUploader
from decouple import config  # type ignore [import-untyped]

ORTHANC_ANON_URL = config("ORTHANC_ANON_URL")
ORTHANC_USERNAME = config("ORTHANC_ANON_USERNAME")
ORTHANC_PASSWORD = config("ORTHANC_ANON_PASSWORD")

DICOMWEB_USERNAME = "orthanc_dicomweb"
DICOMWEB_PASSWORD = "orthanc_dicomweb"  # noqa: S105, hardcoded password

LOCAL_DICOMWEB_URL = "http://localhost:8044"


class MockDicomWebUploader(DicomWebUploader):
    """Mock DicomWebUploader for testing."""

    def __init__(self) -> None:
        """Initialise the mock uploader."""
        self.az_prefix = "test"
        self.orthanc_user = ORTHANC_USERNAME
        self.orthanc_password = ORTHANC_PASSWORD
        self.orthanc_url = ORTHANC_ANON_URL
        self.endpoint_user = DICOMWEB_USERNAME
        self.endpoint_password = DICOMWEB_PASSWORD
        # URL for DICOMWeb server as seen from within Orthanc, i.e. the address of the dicomweb
        # server within the Docker compose network
        self.endpoint_url = "http://dicomweb-server:8042/dicom-web"
        self.orthanc_dicomweb_url = self.orthanc_url + "/dicom-web/servers/" + self.az_prefix
        self.http_timeout = 30


@pytest.fixture()
def dicomweb_uploader() -> MockDicomWebUploader:
    """Fixture to return a mock DicomWebUploader."""
    return MockDicomWebUploader()


def test_dicomweb_server_config(run_containers, dicomweb_uploader) -> None:
    """Tests that the DICOMWeb server is configured correctly in Orthanc"""
    dicomweb_uploader._setup_dicomweb_credentials()  # noqa: SLF001, private method
    servers_response = requests.get(
        ORTHANC_ANON_URL + "/dicom-web/servers",
        auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
        timeout=30,
    )
    servers_response.raise_for_status()
    assert "test" in servers_response.json()


def _check_study_present_on_dicomweb(study_id: str) -> bool:
    """Check if a study is present on the DICOMWeb server."""
    response = requests.get(
        LOCAL_DICOMWEB_URL + "/studies",
        auth=(DICOMWEB_USERNAME, DICOMWEB_PASSWORD),
        timeout=30,
    )
    response.raise_for_status()
    return study_id in response.json()


def _clean_up_dicomweb(study_id: str) -> None:
    """Clean up the DICOMWeb server."""
    response = requests.delete(
        LOCAL_DICOMWEB_URL + "/studies/" + study_id,
        auth=(DICOMWEB_USERNAME, DICOMWEB_PASSWORD),
        timeout=30,
    )
    response.raise_for_status()


def test_upload_dicom_image(
    study_id, run_containers, dicomweb_uploader, not_yet_exported_dicom_image
) -> None:
    """Tests that DICOM image can be uploaded to a DICOMWeb server"""
    response = dicomweb_uploader.send_via_stow(study_id)
    response.raise_for_status()

    # Check that the instance has arrived on the DICOMweb server
    time.sleep(2)
    assert _check_study_present_on_dicomweb(study_id)

    _clean_up_dicomweb(study_id)


def test_dicomweb_upload_fails_with_wrong_credentials(
    study_id, run_containers, dicomweb_uploader
) -> None:
    """Tests that the DICOMWeb uploader fails when given wrong credentials."""
    dicomweb_uploader.endpoint_user = "wrong"
    dicomweb_uploader.endpoint_password = "wrong"  # noqa: S105, hardcoded password

    with pytest.raises(requests.exceptions.ConnectionError):
        dicomweb_uploader._setup_dicomweb_credentials()  # noqa: SLF001, private method


def test_dicomweb_upload_fails_with_wrong_url(study_id, run_containers, dicomweb_uploader) -> None:
    """Tests that the DICOMWeb uploader fails when given wrong URL."""
    dicomweb_uploader.endpoint_url = "http://wrong"

    with pytest.raises(requests.exceptions.ConnectionError):
        dicomweb_uploader._setup_dicomweb_credentials()  # noqa: SLF001, private method
