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
from typing import TYPE_CHECKING

from core.db.models import Image
from core.patient_queue.message import Message
from pixl_cli._io import read_patient_info
from pixl_cli._message_processing import messages_from_df, populate_queue_and_db

if TYPE_CHECKING:
    from pathlib import Path


def test_messages_from_csv(omop_resources: Path) -> None:
    """
    Given a csv with a single dataset.
    When the messages are generated from the directory
    Then one message should be generated
    """
    # Arrange
    test_csv = omop_resources / "test.csv"
    messages_df = read_patient_info(test_csv)
    # Act
    messages = messages_from_df(messages_df)
    # Assert
    assert all(isinstance(msg, Message) for msg in messages)

    expected_messages = [
        Message(
            procedure_occurrence_id=0,
            mrn="patient_identifier",
            accession_number="123456789",
            study_uid="1.2.3.4.5.6.7.8",
            project_name="ms-pinpoint-test",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-01-01T00:01:00Z"),
            study_date=datetime.date.fromisoformat("2022-01-01"),
        ),
    ]
    assert messages == expected_messages


def test_messages_from_csv_with_participant_id(omop_resources: Path) -> None:
    """
    Given a csv with a single dataset that has participant_id defined.
    When the messages are generated from the directory
    Then one message should be generated
    """
    # Arrange
    test_csv = omop_resources / "participant_id.csv"
    messages_df = read_patient_info(test_csv)
    # Act
    messages = messages_from_df(messages_df)
    # Assert
    assert all(isinstance(msg, Message) for msg in messages)

    expected_messages = [
        Message(
            procedure_occurrence_id=0,
            participant_id="AAA00",
            mrn="patient_identifier",
            accession_number="123456789",
            study_uid="1.2.3.4.5.6.7.8",
            project_name="ms-pinpoint-test",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-01-01T00:01:00Z"),
            study_date=datetime.date.fromisoformat("2022-01-01"),
        ),
    ]
    assert messages == expected_messages


def test_messages_from_csv_multiple_projects(
    omop_resources: Path, rows_in_session, mock_publisher
) -> None:
    """
    GIVEN the database has a single Export entity, with one exported Image, one un-exported Image,
    WHEN we parse a file with two projects, each with the same 3 images
      where one project has already exported one of the images
      and the other project has not exported any images
    THEN the database should have 6 Images, with 5 messages returned.
    """
    input_file = omop_resources / "multiple_projects.csv"
    messages_df = read_patient_info(input_file)
    messages = populate_queue_and_db(["imaging"], messages_df)

    # Database has 6 rows now
    images_in_db = rows_in_session.query(Image).all()
    assert len(images_in_db) == 6
    # Exported image filtered out
    assert len(messages) == 5


def test_messages_from_parquet(omop_resources: Path) -> None:
    """
    Given a valid OMOP ES extract with 4 procedures, two of which are x-rays.
    When the messages are generated from the directory and the output of logfile parsing
    Then two messages should be generated
    """
    # Arrange
    omop_parquet_dir = omop_resources / "omop"
    messages_df = read_patient_info(omop_parquet_dir)
    # Act
    messages = messages_from_df(messages_df)
    # Assert
    assert all(isinstance(msg, Message) for msg in messages)

    expected_messages = [
        Message(
            mrn="987654321",
            accession_number="AA12345601",
            study_uid="1.3.6.1.4.1.14519.5.2.1.99.1071.12985477682660597455732044031486",
            study_date=datetime.date.fromisoformat("2020-05-23"),
            procedure_occurrence_id=4,
            project_name="test-extract-uclh-omop-cdm",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
        Message(
            mrn="987654321",
            accession_number="AA12345605",
            study_uid="1.2.276.0.7230010.3.1.2.929116473.1.1710754859.579485",
            study_date=datetime.date.fromisoformat("2020-05-23"),
            procedure_occurrence_id=5,
            project_name="test-extract-uclh-omop-cdm",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
    ]

    assert messages == expected_messages


def test_batch_upload(omop_resources: Path, rows_in_session, mock_publisher) -> None:
    """
    GIVEN the database has a single Export entity, with one exported Image, one unexported Image
    WHEN we parse a file with the two existing images and one new image
    THEN the database should have 3 images, returned messages excludes the exported image.
    """
    input_file = omop_resources / "batch_input.csv"
    messages_df = read_patient_info(input_file)
    messages = populate_queue_and_db(["imaging"], messages_df)

    # Database has 3 rows now
    images_in_db = rows_in_session.query(Image).all()
    assert len(images_in_db) == 3
    # Exported image filtered out
    assert len(messages) == 2


def test_duplicate_upload(omop_resources: Path, rows_in_session, mock_publisher) -> None:
    """
    GIVEN the database has a single Export entity, with one exported Image, one un-exported Image
    WHEN we parse a file with duplicated entries the two existing images and one new image
    THEN the database should have 3 Images, with two message returned.
    """
    input_file = omop_resources / "duplicate_input.csv"
    messages_df = read_patient_info(input_file)
    messages = populate_queue_and_db(["imaging"], messages_df)

    # Database has 3 rows now
    images_in_db = rows_in_session.query(Image).all()
    assert len(images_in_db) == 3
    # Exported and duplicate messages filtered out
    assert len(messages) == 2


def test_participant_id_in_csv(omop_resources: Path, rows_in_session, mock_publisher) -> None:
    """
    GIVEN the database has a single Export entity, with one exported Image, one un-exported Image
    WHEN we parse a file with duplicated entries the two existing images and one new image
    THEN the database should have 3 Images, with two message returned.
    """
    input_file = omop_resources / "duplicate_input.csv"
    messages_df = read_patient_info(input_file)
    messages = populate_queue_and_db(["imaging"], messages_df)

    # Database has 3 rows now
    images_in_db = rows_in_session.query(Image).all()
    assert len(images_in_db) == 3
    # Exported and duplicate messages filtered out
    assert len(messages) == 2
