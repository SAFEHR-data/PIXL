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

from core.rest_api.router import state
from fastapi.testclient import TestClient

from pixl_export.main import app

AppState = state.__class__
client = TestClient(app)


def test_heartbeat_response_is_200() -> None:
    response = client.get("/heart-beat")
    assert response.status_code == 200


def test_initial_state_has_no_token() -> None:
    assert not AppState().token_bucket.has_token(key="primary")
    assert not AppState().token_bucket.has_token(key="secondary")
