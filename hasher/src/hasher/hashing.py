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


# DICOM service requires identifiers to be 1-64 characters long
# and digest is returned as hex encoded i.e. 2 characters per byte
# so do not increase the DIGEST_SIZE
DIGEST_SIZE = 32


@lru_cache
def fetch_key_from_vault() -> str:
    """
    Fetch the key to use in hashing from the Azure Key Vault instance from the env vars.
    Cache the results using unbounded LRU cache. Effectively means the key is
    cached for as long as the process is running so restart the app to clear the cache.

    :return: key
    """
    return "vault"


def generate_hash(message: str) -> str:
    """
    Generate a keyed hash digest from the message using Blake2b

    :param message: string to hash
    :return: hashed string
    """
    key = fetch_key_from_vault()
    return blake2b(
        message.encode("UTF-8"),
        digest_size=DIGEST_SIZE,
        key=key.encode("UTF-8")
    ).hexdigest()
