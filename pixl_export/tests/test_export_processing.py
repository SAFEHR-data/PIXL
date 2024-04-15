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
These tests require executing from within the EHR API container with the dependent
services being up
    - pixl postgres db
    - emap star
"""

from __future__ import annotations

import dataclasses
from logging import getLogger
from typing import Any

import pytest

pytest_plugins = ("pytest_asyncio",)

logger = getLogger(__name__)


@dataclasses.dataclass
class MockResponse:
    """Mock response object for get or post."""

    status_code = 200
    content: str | None
    text: str | None


@pytest.fixture(autouse=True)
def _mock_requests(monkeypatch) -> None:
    """Mock requests so we don't have to run APIs."""

    def mock_get(url: str, params: dict, *args: Any, **kwargs: Any) -> MockResponse:
        logger.info("Mocking request for %s: %s", url, params)
        return MockResponse(
            content="-".join(list(params["message"])), text="-".join(list(params["message"]))
        )

    def mock_post(url: str, data, *args: Any, **kwargs: Any) -> MockResponse:
        logger.info("Mocking request for %s: %s", url, data)
        return MockResponse(content=data + "**DE-IDENTIFIED**", text=data + "**DE-IDENTIFIED**")

    monkeypatch.setattr("requests.get", mock_get)
    monkeypatch.setattr("requests.post", mock_post)
