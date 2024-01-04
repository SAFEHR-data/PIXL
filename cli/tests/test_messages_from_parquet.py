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
"""Unit tests for reading cohorts from parquet files."""
from __future__ import annotations

import datetime
from pathlib import Path

from core.patient_queue.message import Message
from pixl_cli._io import copy_parquet_return_logfile_fields, messages_from_parquet


def test_messages_from_parquet(resources: Path) -> None:
    """
    Given a valid OMOP ES extract directory that has had the logfile parsed
    When the messages are generated from the directory and the output of logfile parsing
    Then the messages should match expected values
    """
    # Arrange
    omop_parquet_dir = resources / "omop"
    project_name, omop_es_datetime = copy_parquet_return_logfile_fields(omop_parquet_dir)
    # Act
    messages = messages_from_parquet(omop_parquet_dir, project_name, omop_es_datetime)
    # Assert
    assert all(isinstance(msg, Message) for msg in messages)

    expected_messages = [
        Message(
            mrn="12345678",
            accession_number="12345678",
            study_date=datetime.date.fromisoformat("2021-07-01"),
            procedure_occurrence_id=1,
            project_name="test-extract-uclh-omop-cdm",
            omop_es_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
        Message(
            mrn="12345678",
            accession_number="ABC1234567",
            study_date=datetime.date.fromisoformat("2021-07-01"),
            procedure_occurrence_id=2,
            project_name="test-extract-uclh-omop-cdm",
            omop_es_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
        Message(
            mrn="987654321",
            accession_number="ABC1234560",
            study_date=datetime.date.fromisoformat("2020-05-01"),
            procedure_occurrence_id=3,
            project_name="test-extract-uclh-omop-cdm",
            omop_es_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
        Message(
            mrn="5020765",
            accession_number="MIG0234560",
            study_date=datetime.date.fromisoformat("2015-05-01"),
            procedure_occurrence_id=4,
            project_name="test-extract-uclh-omop-cdm",
            omop_es_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
    ]

    assert messages == expected_messages
