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

TEST_PROJECT_SLUG = "test_project_slug"


def test_heart_beat_endpoint():
    response = client.get("/heart-beat")
    assert response.status_code == 200
    assert response.json() == "OK"


def test_hash_endpoint_with_default_length():
    response = client.get("/hash", params={"project_slug": TEST_PROJECT_SLUG, "message": "test"})
    expected = "cc8ab6f3e63235b45f3d00cbc4873efac59bf15cec4bdffd461882d57dfc010f"
    assert response.status_code == 200
    assert response.text == expected


def test_hash_endpoint_with_custom_length():
    response = client.get(
        "/hash", params={"project_slug": TEST_PROJECT_SLUG, "message": "test", "length": 16}
    )
    expected = "b721eef65328a79c"
    assert response.status_code == 200
    assert response.text == expected
