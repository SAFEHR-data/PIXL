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

import os
from typing import TYPE_CHECKING

import pytest
from hasher.hashing import Hasher  # type: ignore [import-untyped]

if TYPE_CHECKING:
    from pytest_pixl.keyvault import MockKeyVault  # type: ignore [import-untyped]

os.environ["ENV"] = "test"


@pytest.fixture()
def _dummy_key(monkeypatch):  # noqa: ANN202
    """Fixture to set up a dummy key to use for hashing tests"""
    import hasher.hashing  # type: ignore [import-untyped]

    monkeypatch.setattr(hasher.hashing, "fetch_key_from_vault", lambda: "test-key")


@pytest.fixture(scope="module")
def monkeymodule():
    """Module level monkey patch."""
    from _pytest.monkeypatch import MonkeyPatch

    monkeypatch = MonkeyPatch()
    yield monkeypatch
    monkeypatch.undo()


class MockHasher(Hasher):
    """Mock the Hasher clas without setting a connection to the Azure Key Vault instance."""

    def __init__(self, keyvault: MockKeyVault) -> None:
        """
        Initialise the Hasher instance without setting up the connection to the Azure Key Vault
        instance.
        """
        self.keyvault = keyvault


@pytest.fixture(autouse=True, scope="module")
def mock_hasher(monkeymodule, azure_keyvault) -> Hasher:
    """
    Mock the Hasher class as a pytest fixture.
    Uses the azure_kevyault fixture from pytest_pixl to mock the Azure Key Vault instance.
    """
    hasher = MockHasher(azure_keyvault)
    monkeymodule.setattr("hasher.hashing", hasher)

    return hasher
