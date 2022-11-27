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

from pixl_dcmd.main import (
    combine_date_time,
    get_bounded_age,
    get_encrypted_uid,
    remove_overlays,
)
import pydicom
from pydicom.data import get_testdata_files
import pytest


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
    "test_ages,expected_ages",
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


@pytest.mark.parametrize(
    "orig_date, orig_time, expected_date_time",
    [
        ("20180512", "000000", "20180512 000000.000000"),
        ("20201202", "230000", "20201202 230000.000000"),
        ("20151112", "021415", "20151112 021415.000000"),
        ("20120504", "021312", "20120504 021312.000000"),
        ("20030103", "200203", "20030103 200203.000000"),
        ("19991212", "081415.11", "19991212 081415.110000"),
        ("20210801", "081415.999999", "20210801 081415.999999"),
    ],
)
def test_date_time_combo(
    orig_date: str, orig_time: str, expected_date_time: str
) -> None:
    """Checks that dates and times are combined correctly."""
    assert (
        combine_date_time(orig_date, orig_time).format("YYYYMMDD HHmmss.SSSSSS")
        == expected_date_time
    )


# @pytest.mark.parametrize(
#     "orig_time,offset,expected_shifted_time",
#     [
#         ("020000", 2, "000000"),
#         ("020000", 3, "230000"),
#         ("131415", 11, "021415"),
#         ("141312", 12, "021312"),
#         ("010203", 5, "200203"),
#         ("131415.11", 5, "081415.11"),
#         ("131415.999999", 5, "081415.999999"),
#     ],
# )
# def test_time_const(orig_time: str, offset: int, expected_shifted_time: str) -> None:
#     """Checks that times are shifted relative to offset."""
#     assert subtract_time_const(orig_time, offset) == expected_shifted_time


def test_remove_overlay_plane() -> None:
    """Checks that overlay planes are removed."""
    fpath = get_testdata_files("MR-SIEMENS-DICOM-WithOverlays.dcm")[0]
    ds = pydicom.dcmread(fpath)
    assert (0x6000, 0x3000) in ds

    ds_minus_overlays = remove_overlays(ds)
    assert (0x6000, 0x3000) not in ds_minus_overlays


# TODO
# def test_anonymisation
