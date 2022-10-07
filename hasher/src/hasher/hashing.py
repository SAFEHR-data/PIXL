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

from functools import lru_cache
from hashlib import blake2b
import logging

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from hasher.settings import AZURE_KEY_VAULT_NAME, AZURE_KEY_VAULT_SECRET_NAME

logger = logging.getLogger(__name__)


@lru_cache
def fetch_key_from_vault() -> str:
    """
    Fetch the key to use in hashing from the Azure Key Vault instance specified
    in the environment variables.
    Creates an EnvironmentCredential via AzureDefaultCredential to connect with a
    ServicePrincipal and secret configured via environment variables.
    Cache the results using unbounded LRU cache. Effectively means the key is
    cached for as long as the process is running so restart the app to clear the cache.

    :return: key
    """
    key_vault_uri = f"https://{AZURE_KEY_VAULT_NAME}.vault.azure.net"
    credentials = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault_uri, credential=credentials)
    key = client.get_secret(AZURE_KEY_VAULT_SECRET_NAME)
    if key.value is None:
        raise ValueError("Azure Key Vault secret is None")
    else:
        return key.value


def generate_hash(message: str) -> str:
    """
    Generate a keyed hash digest from the message using Blake2b algorithm.
    The Azure DICOM service requires identifiers to be 1-64 characters long
    and digest is returned as hex encoded i.e. 2 characters per byte
    so do not increase the DIGEST_SIZE

    :param message: string to hash
    :return: hashed string
    """
    key = fetch_key_from_vault()
    return blake2b(
        message.encode("UTF-8"), digest_size=32, key=key.encode("UTF-8")
    ).hexdigest()
