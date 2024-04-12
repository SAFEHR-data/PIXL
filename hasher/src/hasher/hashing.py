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
import secrets
from hashlib import blake2b

from core.project_config.secrets import AzureKeyVault  # type: ignore [import-untyped]
from decouple import config  # type: ignore [import-untyped]

logger = logging.getLogger(__name__)


class Hasher:
    """
    Hasher class to generate keyed hash digests using the Blake2b algorithm and fetch the
    salt for a specific project from the Azure Key Vault instance.
    """

    def __init__(self, project_slug: str) -> None:
        """
        Initialise the Hasher instance for a specific project and set up connection to
        the AzureKeyVault instance.
        """
        self.project_slug = project_slug
        self.keyvault = AzureKeyVault()

    def generate_hash(self, message: str, length: int = 64, *, override_salt: bool = False) -> str:
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

        key = self.keyvault.fetch_secret(config("AZURE_KEY_VAULT_SECRET_NAME"))

        # Apply salt from the keyvault and local salt if it exists
        message += self._fetch_salt(length=length, override=override_salt)
        message += config("LOCAL_SALT_VALUE", default="")

        return blake2b(
            message.encode("UTF-8"), digest_size=output_bytes, key=key.encode("UTF-8")
        ).hexdigest()

    def _fetch_salt(self, length: int = 16, *, override: bool) -> str:
        """
        Fetch the salt for a specific project to use in hashing from the Azure Key Vault instance
        :param project_name: the name of the project to fetch the salt for
        :param length: number of characters for the salt, should be between 2 and 64
        :return: salt
        """
        try:
            salt = self.keyvault.fetch_secret(self.project_slug)

            if override & len(salt) != length:
                msg = f"Existing salt for {self.project_slug} is of different length. Regenerating."
                logger.warning(msg)
                salt = _generate_salt(length)
                self.keyvault.create_secret(self.project_slug, salt)

        except ValueError:
            msg = f"No existing salt for project {self.project_slug}, generating a new one."
            logger.warning(msg)
            salt = _generate_salt(length)
            self.keyvault.create_secret(self.project_slug, salt)
        return salt


def _generate_salt(length: int = 16) -> str:
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
