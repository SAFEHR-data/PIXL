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
"""
The main hashing functionality

This module provides:
- fetch_key_from_vault: fetch the hashing key from the Azure Key Vault instance
- generate_hash: generate a keyed hash digest using the Blake2b algorithm
- generate_salt: generate a random text string in hexadecimal to be used as a salt

"""

from __future__ import annotations

import logging
import os
import secrets
from functools import lru_cache
from hashlib import blake2b

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from core.project_config.secrets import AzureKeyVault

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
    if os.environ.get("ENV", None) == "test":
        return "test_key"

    key_vault_uri = f"https://{AZURE_KEY_VAULT_NAME}.vault.azure.net"
    credentials = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault_uri, credential=credentials)
    key = client.get_secret(AZURE_KEY_VAULT_SECRET_NAME)
    if key.value is None:
        msg = "Azure Key Vault secret is None"
        raise ValueError(msg)

    return str(key.value)


def generate_hash(message: str, length: int = 64) -> str:
    """
    Generate a keyed hash digest from the message using Blake2b algorithm.
    The Azure DICOM service requires identifiers to be less than 64 characters.

    :param message: string to hash
    :param length: maximum number of characters in the output (2 <= length <= 64)
    :return: hashed string
    """
    max_length = 64
    min_length = 2
    if length > max_length:
        msg = f"Maximum hash length is 64 characters, received: {length}"
        raise ValueError(msg)

    if length < min_length:
        msg = f"Minimum hash length is 2 characters, received: {length}"
        raise ValueError(msg)

    # HMAC digest is returned as hex encoded i.e. 2 characters per byte
    output_bytes = length // 2

    key = fetch_key_from_vault()
    return blake2b(
        message.encode("UTF-8"), digest_size=output_bytes, key=key.encode("UTF-8")
    ).hexdigest()


def generate_salt(length: int = 16) -> str:
    """
    Generate a random text string in hexadecimal to be used as a salt.

    :param length: maximum number of characters in the output (2 <= length <= 64)
    :return: hexadecimal string
    """
    max_length = 64
    min_length = 2
    if length > max_length:
        msg = f"Maximum salt length is 64 characters, received: {length}"
        raise ValueError(msg)

    if length < min_length:
        msg = f"Minimum salt length is 2 characters, received: {length}"
        raise ValueError(msg)

    # Output is hex encoded i.e. 2 characters per byte
    output_bytes = length // 2

    return secrets.token_hex(output_bytes)


def fetch_salt(project_name: str) -> str:
    """
    Fetch the salt for a specific project to use in hashing from the Azure Key Vault instance
    :param project_name: the name of the project to fetch the salt for
    :return: salt
    """
    keyvault = AzureKeyVault()
    try:
        salt = keyvault.fetch_secret(project_name)
    except ValueError:
        msg = f"No existing salt for project {project_name}, generating a new one."
        logger.warning(msg)
        salt = generate_salt()
        keyvault.create_secret(project_name, salt)
    return salt
