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
"""Helper functions for de-identification."""

import hashlib
import re

from logging import getLogger

logger = getLogger(__name__)


def get_encrypted_uid(uid: str, salt: bytes) -> str:
    """
    Hashes the suffix of a DICOM UID with the given salt.

    This function retains the prefix, while sha512-hashing the subcomponents
    of the suffix. The number of digits per subcomponent is retained in the
    encrypted UID. This also ensures that no UID is greater than 64 chars.
    No leading zeros are permitted in a subcomponent unless the subcomponent
    has a length of 1.

    Original UID:	    1.2.124.113532.10.122.1.203.20051130.122937.2950157
    Encrypted UID:	1.2.124.113532.74.696.4.703.80155569.949794.5833842

    Encrypting the UIDs this way ensures that no time information remains but
    that a input UID will always result in the same output UID, for a given salt.

    Note. that while no application should ever rely on the structure of a UID,
    there is a possibility that the were the anonyimised data to be push to the
    originating scanner (or scanner type), the data may not be recognised.
    """
    uid_elements = uid.split(".")

    prefix = ".".join(uid_elements[:4])
    suffix = ".".join(uid_elements[4:])
    logger.debug(f"\t\tPrefix: {prefix}")
    logger.debug(f"\t\tSuffix: {suffix}")

    # Get subcomponents of suffix as array.
    suffix_elements = uid_elements[4:]
    enc_element = [""] * len(suffix_elements)

    # For each subcomponent of the suffix:
    for idx, item in enumerate(suffix_elements):
        h = hashlib.sha512()
        h.update(item.encode("utf-8"))  # Add subcomponent.
        h.update(salt)  # Apply salt.

        # If subcomponent has a length of one, allow a leading zero, otherwise
        # strip leading zeros.
        # Regex removes any non-numeric chars.
        if len(item) == 1:
            enc_element[idx] = re.sub("[^0-9]", "", h.hexdigest())[: len(item)]
        else:
            enc_element[idx] = re.sub("[^0-9]", "", h.hexdigest()).lstrip("0")[
                : len(item)
            ]

    # Return original prefix and encrypted suffix.
    return prefix + "." + ".".join(enc_element[:])


def get_bounded_age(age: str) -> str:
    """Bounds patient age between 18 and 89"""
    if age[3] != "Y":
        return "018Y"

    age_as_int = int(age[0:3])
    if age_as_int < 18:
        return "018Y"

    if age_as_int > 89:
        return "089Y"

    return age
