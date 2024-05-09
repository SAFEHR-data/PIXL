#  Copyright (c) University College London Hospitals NHS Foundation Trust
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

"""Test functions in _io.py."""

from datetime import date
from pathlib import Path

import pytest
from core.db.models import Extract, Image
from pixl_cli._io import make_radiology_linker_table, messages_from_csv
from pydicom.uid import generate_uid


def test_message_from_csv_raises_for_malformed_input(tmpdir):
    """Test that messages_from_csv raises for malformed input."""
    # Create a CSV file with the wrong column names
    csv_file = tmpdir.join("malformed.csv")
    csv_file.write("procedure_id,mrn,accession_number,extract_generated_timestamp,study_date\n")
    csv_file.write("1,123,1234,01/01/2021 00:00,01/01/2021\n")
    with pytest.raises(ValueError, match=".*expected to have at least.*"):
        messages_from_csv(csv_file)


def test_make_radiology_linker_table(omop_resources: Path):
    """
    Given some fake image data that normally would be from the database,
    make a dataframe containing the radiology linker table data.
    """
    extract = Extract(extract_id=1, slug="whatever")
    images = [
        Image(
            accession_number="AA12345601",
            study_date=date(1, 1, 1),
            mrn="987654321",
            pseudo_study_uid=generate_uid(entropy_srcs=["test_pseudo_id_1"]),
            extract=extract,
        ),
        Image(
            accession_number="AA12345605",
            study_date=date(1, 1, 1),
            mrn="987654321",
            pseudo_study_uid=generate_uid(entropy_srcs=["test_pseudo_id_2"]),
            extract=extract,
        ),
        Image(
            accession_number="different_should_ignore",
            study_date=date(1, 1, 1),
            mrn="987654321",
            pseudo_study_uid=generate_uid(entropy_srcs=["should_never_see_1"]),
            extract=extract,
        ),
        Image(
            accession_number="AA12345605",
            study_date=date(1, 1, 1),
            mrn="different_should_ignore",
            pseudo_study_uid=generate_uid(entropy_srcs=["should_never_see_2"]),
            extract=extract,
        ),
    ]
    linker_df = make_radiology_linker_table(omop_resources / "omop", images)

    po_col = linker_df["procedure_occurrence_id"]
    row_po_4 = linker_df[po_col == 4].iloc[0]
    row_po_5 = linker_df[po_col == 5].iloc[0]
    assert row_po_4.pseudo_study_uid == "test_pseudo_id_1"
    assert row_po_5.pseudo_study_uid == "test_pseudo_id_2"

    assert linker_df.shape[0] == 2
    assert set(linker_df.columns) == {"procedure_occurrence_id", "pseudo_study_uid"}
