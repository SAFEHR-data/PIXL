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

import pytest

os.environ["ENV"] = "test"
os.environ["AZURE_KEY_VAULT_SECRET_NAME"] = "test-key"  # noqa: S105, hardcoded secret


@pytest.fixture(autouse=True)
def _mock_hasher(monkeypatch) -> None:
    """
    Mock the Hasher class as a pytest fixture.
    Uses the azure_kevyault fixture from pytest_pixl to mock the Azure Key Vault instance.
    """
    import hasher  # type: ignore [import-untyped]
    from pytest_pixl.keyvault import MockKeyVault  # type: ignore [import-untyped]

    mock_keyvault = MockKeyVault()
    mock_keyvault.create_secret("test-key", "test-key")

    def mock_hasher_init(self) -> None:
        self.keyvault = mock_keyvault

    monkeypatch.setattr(hasher.hashing.Hasher, "__init__", mock_hasher_init)
