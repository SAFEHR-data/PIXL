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

"""Test datetime helpers."""
import pytest

from pixl_dcmd._datetime import combine_date_time, format_date_time


@pytest.mark.parametrize(
    ("orig_date", "orig_time", "expected_date_time"),
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


@pytest.mark.parametrize(
    ("orig_date_time", "output_date_time"),
    [
        ("20220430163109", "20220430 163109.000000"),
        ("20220101003557.000000", "20220101 003557.000000"),
        ("20220101 003557.000000", "20220101 003557.000000"),
    ],
)
def test_date_time_format(orig_date_time: str, output_date_time: str) -> None:
    """Checks that dates and times are formatted correctly."""
    assert (
        format_date_time(orig_date_time).format("YYYYMMDD HHmmss.SSSSSS")
        == output_date_time
    )
