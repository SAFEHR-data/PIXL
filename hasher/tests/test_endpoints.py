#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
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
from __future__ import annotations

from fastapi.testclient import TestClient
from hasher.main import app  # type: ignore [import-untyped]

client = TestClient(app)


def test_heart_beat_endpoint():
    response = client.get("/heart-beat")
    assert response.status_code == 200
    assert response.json() == "OK"


def test_hash_endpoint_with_default_length():
    response = client.get("/hash", params={"message": "test"})
    expected = "270426312ab76c2f0df60b6cef3d14aab6bc17219f1a76e63edf88a8f705c17a"
    assert response.status_code == 200
    assert response.text == expected


def test_hash_endpoint_with_custom_length():
    response = client.get("/hash", params={"message": "test", "length": 16})
    expected = "b88ea642703eed33"
    assert response.status_code == 200
    assert response.text == expected


def test_salt_endpoint_with_default_length():
    response = client.get("/salt", params={"project_name": "test"})
    assert response.status_code == 200
    assert len(response.text) == 16


def test_salt_endpoint_with_custom_length():
    response = client.get("/salt", params={"project_name": "test", "length": 8})
    assert response.status_code == 200
    assert len(response.text) == 8


def test_accession_number_endpoint_returns_dicom_compatible_hash():
    """
    Accession number/study ID is a short string (at most 16 characters). See:
    https://dicom.innolitics.com/ciods/12-lead-ecg/general-study/00200010
    https://dicom.nema.org/dicom/2013/output/chtml/part05/sect_6.2.html
    """
    response = client.get("/hash-accession-number", params={"message": "test_accession_number"})
    assert len(response.text) <= 16


def test_mrn_endpoint_returns_dicom_compatible_hash():
    """
    Patient identifier can be a long string. See:
    https://dicom.innolitics.com/ciods/rt-plan/patient/00101002/00100020
    """
    response = client.get("/hash-mrn", params={"message": "test_mrn"})
    assert len(response.text) <= 64
