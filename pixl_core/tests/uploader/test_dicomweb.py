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
from decouple import config  # type: ignore [import-untyped]

ORTHANC_URL = config("ORTHANC_URL")
ORTHANC_USERNAME = config("ORTHANC_USERNAME")
ORTHANC_PASSWORD = config("ORTHANC_PASSWORD")
DICOMWEB_USERNAME = config("DICOMWEB_USERNAME")
DICOMWEB_PASSWORD = config("DICOMWEB_PASSWORD")
DICOMWEB_URL = config("DICOMWEB_URL")

LOCAL_DICOMWEB_URL = "http://localhost:8044"


class MockDicomWebUploader(DicomWebUploader):
    """Mock DicomWebUploader for testing."""

    def __init__(self) -> None:
        """Initialise the mock uploader."""
        self.az_prefix = "test"
        self.orthanc_user = ORTHANC_USERNAME
        self.orthanc_password = ORTHANC_PASSWORD
        self.orthanc_url = ORTHANC_URL
        self.endpoint_user = DICOMWEB_USERNAME
        self.endpoint_password = DICOMWEB_PASSWORD
        self.endpoint_url = DICOMWEB_URL
        self.orthanc_dicomweb_url = self.orthanc_url + "/dicom-web/servers/" + self.az_prefix


@pytest.fixture()
def dicomweb_uploader() -> MockDicomWebUploader:
    """Fixture to return a mock DicomWebUploader."""
    return MockDicomWebUploader()


def test_dicomweb_server_config(run_containers, dicomweb_uploader) -> None:
    """Tests that the DICOMWeb server is configured correctly in Orthanc"""
    dicomweb_uploader._setup_dicomweb_credentials()  # noqa: SLF001, private method
    servers_response = requests.get(
        ORTHANC_URL + "/dicom-web/servers",
        auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
        timeout=30,
    )

    assert "test" in servers_response.json()


def _check_study_present_on_dicomweb(study_id: str) -> bool:
    """Check if a study is present on the DICOMWeb server."""
    response = requests.get(
        LOCAL_DICOMWEB_URL + "/studies",
        auth=(DICOMWEB_USERNAME, DICOMWEB_PASSWORD),
        timeout=30,
    )
    return any(study == study_id for study in response.json())


def test_upload_dicom_image(study_id, run_containers, dicomweb_uploader) -> None:
    """Tests that DICOM image can be uploaded to a DICOMWeb server"""
    stow_response = dicomweb_uploader.send_via_stow(study_id)
    assert stow_response.status_code == 200  # succesful upload

    # Check that the instance has arrived on the DICOMweb server
    time.sleep(2)
    assert _check_study_present_on_dicomweb(study_id)

    # Clean up
    requests.delete(
        LOCAL_DICOMWEB_URL + "/studies/" + study_id,
        auth=(DICOMWEB_USERNAME, DICOMWEB_PASSWORD),
        timeout=30,
    )


def test_dicomweb_upload_fails_with_wrong_credentials(
    study_id, run_containers, dicomweb_uploader
) -> None:
    """Tests that the DICOMWeb uploader fails when given wrong credentials."""
    dicomweb_uploader.endpoint_user = "wrong"
    dicomweb_uploader.endpoint_password = "wrong"  # noqa: S105, hardcoded password

    # Force updating of the credentials, so we don't need to restart the container
    dicomweb_uploader._setup_dicomweb_credentials()  # noqa: SLF001, private method

    dicomweb_uploader.send_via_stow(study_id)
    assert not _check_study_present_on_dicomweb(study_id)


def test_dicomweb_upload_fails_with_wrong_url(study_id, run_containers, dicomweb_uploader) -> None:
    """Tests that the DICOMWeb uploader fails when given wrong URL."""
    dicomweb_uploader.endpoint_url = "wrong"
    # Force updating of the credentials, so we don't need to restart the container
    dicomweb_uploader._setup_dicomweb_credentials()  # noqa: SLF001, private method

    dicomweb_uploader.send_via_stow(study_id)
    assert not _check_study_present_on_dicomweb(study_id)
