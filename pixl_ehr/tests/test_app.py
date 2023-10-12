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
"""
This file contains unit tests for the API that do not require any test services
"""
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
