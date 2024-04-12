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
os.environ["LOCAL_SALT_VALUE"] = "pixl_salt"


class MockKeyVault:
    """Mock KeyVault class for testing."""

    def __init__(self) -> None:
        """Create a mock instance of a KeyVault."""
        self.secrets: dict[str, str] = {}

    def fetch_secret(self, secret_name: str) -> str:
        """Mock method to fetch a secret from the Key Vault."""
        try:
            return self.secrets[secret_name]

        # Raise a ValueError if the secret is not found, to mimic real Key Vault behaviour
        except KeyError as err:
            raise ValueError from err

    def create_secret(self, secret_name: str, secret_value: str) -> None:
        """Mock method to create a secret in the Key Vault."""
        self.secrets[secret_name] = secret_value


@pytest.fixture(autouse=True)
def _mock_hasher(monkeypatch) -> None:
    """
    Mock the Hasher class as a pytest fixture.
    Uses the azure_kevyault fixture from pytest_pixl to mock the Azure Key Vault instance.
    """
    import hasher  # type: ignore [import-untyped]

    mock_keyvault = MockKeyVault()
    # Create the hashing secret in the mock KeyVault
    mock_keyvault.create_secret("test-key", "test-key")

    def mock_hasher_init(self, project_slug: str) -> None:
        self.keyvault = mock_keyvault
        self.project_slug = project_slug
        # Set an initial salt value for testing
        self.keyvault.create_secret(project_slug, "a161577b49a9235a")

    monkeypatch.setattr(hasher.hashing.Hasher, "__init__", mock_hasher_init)
