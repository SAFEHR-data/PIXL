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
"""This file contains unit tests for the API that do not require any test services"""
from __future__ import annotations

from core.project_config import PixlConfig
from fastapi.testclient import TestClient
from pixl_ehr.main import app, state

AppState = state.__class__
client = TestClient(app)


def test_heartbeat_response_is_200() -> None:
    response = client.get("/heart-beat")
    assert response.status_code == 200


def test_initial_state_has_no_token() -> None:
    assert not AppState().token_bucket.has_token


def test_updating_the_token_refresh_rate_to_negative_fails() -> None:
    response = client.post("/token-bucket-refresh-rate", json={"rate": -1})
    assert response.is_error


def test_updating_the_token_refresh_rate_to_string_fails() -> None:
    response = client.post("/token-bucket-refresh-rate", json={"rate": "a string"})
    assert response.is_error


def test_updating_the_token_refresh_rate_updates_state() -> None:
    response = client.post("/token-bucket-refresh-rate", json={"rate": 1})
    assert state.token_bucket.has_token
    assert response.status_code == 200

    response = client.get("/token-bucket-refresh-rate")
    assert response.text == '{"rate":1.0}'

    # This test uses shared global state, which must be reverted... not ideal.
    state.token_bucket = AppState().token_bucket


def test_non_ftp_upload_destination_fails(monkeypatch) -> None:
    export_params = {
        "project_name": "test-extract-uclh-omop-cdm",
        "extract_datetime": "2024-01-10T00:00:00Z",
        "output_dir": "patient",
    }
    # mock export_radiology_as_parquet
    # app.dependency_overrides[export_radiology_as_parquet] = lambda: None  # noqa: ERA001
    monkeypatch.setattr("pixl_ehr.main.export_radiology_as_parquet", lambda x: None)  # noqa: ARG005
    # mock load_project_config
    project_config = PixlConfig.model_validate(
        {
            "project": {"name": "some-project", "modalities": ["radiology"]},
            "tag_operation_files": "test-extract-uclh-omop-cdm-tag-operations.yaml",
            "destination": {"dicom": "none", "parquet": "none"},
        }
    )
    # app.dependency_overrides[load_project_config] = lambda x: project_config  # noqa: ERA001
    monkeypatch.setattr("core.project_config.load_project_config", lambda x: project_config)  # noqa: ARG005
    # app.dependency_overrides[upload_parquet_files] = lambda: None  # noqa: ERA001
    monkeypatch.setattr("pixl_ehr.main.upload_parquet_files", lambda x: None)  # noqa: ARG005
    # assert http exception raised
    # with pytest.raises(HTTPException):
    response = client.post("/export-patient-data", json=export_params)
    assert response.status_code == 400
