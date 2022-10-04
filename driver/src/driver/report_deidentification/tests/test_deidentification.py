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
from typing import Tuple

from driver.report_deidentification import deidentify_text
import pytest

THIS_DIR = Path(os.path.dirname(os.path.abspath(__file__)))


def _patient_names_from_names_csv() -> list:
    """From a csv file with a header and an index column extract name tuples"""

    def _tuple_from(line: str) -> Tuple[str, str]:
        items = line.split(",")
        return items[1], items[2]

    path = THIS_DIR / "data" / "names.csv"

    return [_tuple_from(line) for line in open(path, "r").readlines()[1:]]


@pytest.mark.parametrize("full_name", _patient_names_from_names_csv())
def test_patient_name_is_redacted(full_name: Tuple[str, str]) -> None:

    first_name, last_name = full_name
    report_text = f"{first_name} {last_name} was x rayed and the prognosis is X"
    anon_text = deidentify_text(report_text)

    for name in (first_name, last_name):
        assert name not in anon_text
