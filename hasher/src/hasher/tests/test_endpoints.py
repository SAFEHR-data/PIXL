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

from fastapi.testclient import TestClient

from hasher.main import app

client = TestClient(app)


def test_heart_beat_endpoint():
    response = client.get("/heart-beat")
    assert response.status_code == 200
    assert response.json() == "OK"


def test_hashing_endpoint(dummy_key):
    response = client.post("/hash", params={"message": "test"})
    expected = "270426312ab76c2f0df60b6cef3d14aab6bc17219f1a76e63edf88a8f705c17a"
    assert response.status_code == 200
    assert response.text == expected
