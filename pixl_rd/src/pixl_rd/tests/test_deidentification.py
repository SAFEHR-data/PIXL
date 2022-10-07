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

import os
from pathlib import Path
from typing import List, Tuple

import pytest

from pixl_rd import deidentify_text

THIS_DIR = Path(os.path.dirname(os.path.abspath(__file__)))


def _patient_names_from_names_csv() -> List[Tuple[str, str]]:
    """From a csv file with a header and an index column extract name tuples"""

    def _tuple_from(line: str) -> Tuple[str, str]:
        items = line.split(",")
        return items[1], items[2]

    path = THIS_DIR / "data" / "names.csv"

    return [_tuple_from(line) for line in open(path, "r").readlines()[1:]]


def test_patient_name_is_redacted(required_accuracy: float = 0.95) -> None:

    results = []

    for first_name, last_name in _patient_names_from_names_csv():

        report_text = f"{first_name} {last_name} was x-rayed and the prognosis is X"
        anon_text = deidentify_text(report_text)
        results.append(first_name not in anon_text and last_name not in anon_text)

    accuracy_ratio = sum(results) / len(results)
    assert accuracy_ratio > required_accuracy


def test_signed_by_section_is_removed() -> None:
    pass


@pytest.mark.skip(reason="Presidio does not remove all the dates correctly")
@pytest.mark.parametrize("delimiter", ["", " ", "/", "-", ":"])
def test_possible_dates_are_removed(delimiter: str) -> None:

    for day, month, year in [(1, 3, 2019)]:

        date_strings = [
            f"{day}{delimiter}{month}{delimiter}{year}",
            f"{month}{delimiter}{day}{delimiter}{year}",
            f"{year}{delimiter}{month}{delimiter}{day}",
            f"{day:02d}{delimiter}{month:02d}{delimiter}{year}",  # +leading 0
        ]

        anon_text = deidentify_text("\n".join(date_strings))
        assert not any(date_string in anon_text for date_string in date_strings)
