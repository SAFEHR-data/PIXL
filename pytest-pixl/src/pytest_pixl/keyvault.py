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
"""A mock Azure Keyvault instance for testing."""


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
