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

import pytest
import requests
from core.uploader._dicomweb import DicomWebUploader  # type: ignore [import-untyped]
from decouple import config  # type: ignore [import-untyped]

ORTHANC_URL = config("ORTHANC_URL")
DICOM_ENDPOINT_NAME = config("DICOM_ENDPOINT_NAME")
ORTHANC_USERNAME = config("ORTHANC_USERNAME")
ORTHANC_PASSWORD = config("ORTHANC_PASSWORD")


class MockDicomWebUploader(DicomWebUploader):
    """Mock DicomWebUploader for testing."""

    def __init__(self) -> None:
        """Initialise the mock uploader."""
        self.user = ORTHANC_USERNAME
        self.password = ORTHANC_PASSWORD
        self.endpoint_name = DICOM_ENDPOINT_NAME
        self.orthanc_url = ORTHANC_URL
        self.url = self.orthanc_url + "/dicom-web/servers/" + self.endpoint_name


@pytest.fixture()
def dicomweb_uploader() -> MockDicomWebUploader:
    """Fixture to return a mock DicomWebUploader."""
    return MockDicomWebUploader()


def test_upload_dicom_image(dicom_resource, run_dicomweb_containers, dicomweb_uploader) -> None:
    """Tests that DICOM image can be uploaded to a DICOMWeb server"""
    # ARRANGE

    # ACT
    stow_response = dicomweb_uploader.send_via_stow(dicom_resource)

    # ASSERT
    destination_url = ORTHANC_URL + "/dicom-web/studies"
    response = requests.get(
        destination_url,
        auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
        data={"Uri": "/instances"},
        timeout=30,
    )

    assert stow_response.status_code == 200  # succesful upload
    # Taken from https://orthanc.uclouvain.be/hg/orthanc-dicomweb/file/default/Resources/Samples/Python/SendStow.py
    assert "00081190" in response.json()[0]
