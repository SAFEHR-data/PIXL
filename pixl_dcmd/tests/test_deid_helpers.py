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

"""Tests for anonymisation of DICOM data."""

import pytest

from pixl_dcmd._deid_helpers import get_bounded_age, get_encrypted_uid


def test_encrypt_uid_1() -> None:
    """Checks whether UID is hashed with salt=1234567890."""
    test_uid = "1.2.124.113532.10.122.1.203.20051130.122937.2950157"
    test_salt = b"1234567890"
    expected_uid = "1.2.124.113532.28.570.5.537.30525294.945722.5900125"
    assert get_encrypted_uid(test_uid, test_salt) == expected_uid


def test_encrypt_uid_2() -> None:
    """Checks whether UID is hashed with salt=ABCDEFGHIJ."""
    test_uid = "1.2.124.113532.10.122.1.203.20051130.122937.2950157"
    test_salt = b"ABCDEFGHIJ"
    expected_uid = "1.2.124.113532.66.684.0.649.78590783.565647.7283900"
    assert get_encrypted_uid(test_uid, test_salt) == expected_uid


@pytest.mark.parametrize(
    ("test_ages", "expected_ages"),
    [
        ("005D", "018Y"),
        ("010M", "018Y"),
        ("017Y", "018Y"),
        ("018Y", "018Y"),
        ("030Y", "030Y"),
        ("089Y", "089Y"),
        ("100Y", "089Y"),
    ],
)
def test_age_bounding(test_ages: str, expected_ages: str) -> None:
    """Checks ages are bounded between 18 >= x <= 89."""
    assert get_bounded_age(test_ages) == expected_ages
