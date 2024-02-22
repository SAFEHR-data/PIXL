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

"""Handles fetching of project secrets from the Azure Keyvault"""

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from decouple import config

AZURE_KEY_VAULT_NAME = config("EXPORT_AZ_KEY_VAULT_NAME")


def _fetch_secret(secret_name: str) -> str:
    """
    Fetch a secret from the Azure Key Vault instance specified in the environment variables.
    Creates an EnvironmentCredential via AzureDefaultCredential to connect with a
    ServicePrincipal and secret configured via environment variables.

    This requires the following environment variables to be set, which will be picked up by the
    Azure SDK:
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
    - AZURE_TENANT_ID
    - AZURE_KEY_VAULT_NAME

    :return: the requested secret's value
    """
    key_vault_uri = f"https://{AZURE_KEY_VAULT_NAME}.vault.azure.net"
    credentials = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault_uri, credential=credentials)

    secret = client.get_secret(secret_name).value
    if secret is None:
        msg = "Azure Key Vault secret is None"
        raise ValueError(msg)

    return str(secret)
