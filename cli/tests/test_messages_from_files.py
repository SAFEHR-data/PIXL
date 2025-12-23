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

import pytest
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
            series_uid="",
            project_name="ms-pinpoint-test",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-01-01T00:01:00Z"),
            study_date=datetime.date.fromisoformat("2022-01-01"),
        ),
    ]
    assert messages == expected_messages


def test_whitespace_and_na_processing(omop_resources: Path) -> None:
    """
    GIVEN a csv with leading and trailing whitespace, a duplicate entry
      and ones with no image identifiers (empty and whitespaces).
    WHEN the messages are generated from the directory
    THEN one message should be generated, with no leading or trailing whitespace
    """
    # Arrange
    test_csv = omop_resources / "test_whitespace_and_na_processing.csv"
    messages_df = read_patient_info(test_csv)
    # Act
    messages = messages_from_df(messages_df)
    # Assert
    assert messages == [
        Message(
            procedure_occurrence_id=0,
            mrn="patient_identifier",
            accession_number="123456789",
            study_uid="1.2.3.4.5.6.7.8",
            series_uid="",
            project_name="ms-pinpoint-test",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-01-01T00:01:00Z"),
            study_date=datetime.date.fromisoformat("2022-01-01"),
        ),
    ]


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
    messages = populate_queue_and_db(["imaging-primary"], messages_df, messages_priority=1)

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
            series_uid="",
            study_date=datetime.date.fromisoformat("2020-05-23"),
            procedure_occurrence_id=4,
            project_name="test-extract-uclh-omop-cdm",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
        Message(
            mrn="987654321",
            accession_number="AA12345605",
            study_uid="1.2.276.0.7230010.3.1.2.929116473.1.1710754859.579485",
            series_uid="",
            study_date=datetime.date.fromisoformat("2020-05-23"),
            procedure_occurrence_id=5,
            project_name="test-extract-uclh-omop-cdm",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
    ]

    assert messages == expected_messages


def test_messages_from_batched_parquet(omop_resources: Path) -> None:
    """
    Given a valid OMOP ES batched extract with 6 radiology procedures.
    When the messages are generated from the directory
    Then 6 messages should be generated
    """
    # Arrange
    omop_parquet_dir = omop_resources / "omop-batched"
    messages_df = read_patient_info(omop_parquet_dir)
    # Act
    messages = messages_from_df(messages_df)
    # Assert
    assert all(isinstance(msg, Message) for msg in messages)

    expected_messages = [
        Message(
            mrn="5020765",
            accession_number="MIG0234560",
            study_uid="1.2.840.114350.2.525.2.798268.2.110000014.1",
            series_uid="",
            study_date=datetime.date(2015, 5, 1),
            procedure_occurrence_id=4.0,
            project_name="test-extract-uclh-omop-cdm",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
        Message(
            mrn="987654321",
            accession_number="ABC1234560",
            study_uid="1.2.840.114350.2.525.2.798268.2.190000013.1",
            series_uid="",
            study_date=datetime.date(2020, 5, 1),
            procedure_occurrence_id=3.0,
            project_name="test-extract-uclh-omop-cdm",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
        Message(
            mrn="987654321",
            accession_number="AA12345601",
            study_uid="1.2.840.114350.2.525.2.798268.2.190000015.1",
            series_uid="",
            study_date=datetime.date(2020, 5, 23),
            procedure_occurrence_id=5.0,
            project_name="test-extract-uclh-omop-cdm",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
        Message(
            mrn="987654321",
            accession_number="AA12345605",
            study_uid="1.2.840.114350.2.525.2.798268.2.190000016.1",
            series_uid="",
            study_date=datetime.date(2020, 5, 23),
            procedure_occurrence_id=6.0,
            project_name="test-extract-uclh-omop-cdm",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
        Message(
            mrn="12345678",
            accession_number="12345678",
            study_uid="1.2.840.114350.2.525.2.798268.2.190000011.1",
            series_uid="",
            study_date=datetime.date(2021, 7, 1),
            procedure_occurrence_id=1.0,
            project_name="test-extract-uclh-omop-cdm",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
        Message(
            mrn="12345678",
            accession_number="ABC1234567",
            study_uid="1.2.840.114350.2.525.2.798268.2.190000012.1",
            series_uid="",
            study_date=datetime.date(2021, 7, 1),
            procedure_occurrence_id=2.0,
            project_name="test-extract-uclh-omop-cdm",
            extract_generated_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
    ]

    assert messages == expected_messages


def test_input_directory_does_not_have_public_directory(omop_resources: Path) -> None:
    """
    Given a directory that does not have a public or private directory
    When the messages are generated from the directory
    Then a NotADirectoryError should be raised
    """
    # Arrange
    omop_parquet_dir = omop_resources / "omop-batched" / "public"
    with pytest.raises(NotADirectoryError):
        read_patient_info(omop_parquet_dir)


def test_batch_upload(omop_resources: Path, rows_in_session, mock_publisher) -> None:
    """
    GIVEN the database has a single Export entity, with one exported Image, one unexported Image
    WHEN we parse a file with the two existing images and one new image with no participant_ids
    THEN the database should have 3 images, and returned messages excludes the exported image.
    """
    input_file = omop_resources / "batch_input.csv"
    messages_df = read_patient_info(input_file)
    messages = populate_queue_and_db(["imaging-primary"], messages_df, messages_priority=1)

    # Database has 3 rows now
    images_in_db: list[Image] = rows_in_session.query(Image).all()
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
    messages = populate_queue_and_db(["imaging-primary"], messages_df, messages_priority=1)

    # Database has 3 rows now
    images_in_db = rows_in_session.query(Image).all()
    assert len(images_in_db) == 3
    # Exported and duplicate messages filtered out
    assert len(messages) == 2


def test_upload_with_participant_id(omop_resources: Path, db_session, mock_publisher) -> None:
    """
    GIVEN the database is empty,
    WHEN we parse a file with the images that have participant_ids,
    THEN the database should have 3 images and the `pseudo_patient_id`s in the database should
    math the participant_ids in the CSV file.
    """
    input_file = omop_resources / "participant_id.csv"
    messages_df = read_patient_info(input_file)
    messages = populate_queue_and_db(["imaging-primary"], messages_df, messages_priority=1)

    # Database has 3 rows now
    images_in_db: list[Image] = db_session.query(Image).all()
    assert len(images_in_db) == 3
    # A message per image
    assert len(messages) == 3
    # Pseudo_patient_id for new image is same as participant_ids in CSV file
    assert images_in_db[0].pseudo_patient_id == "AAA00"
    assert images_in_db[1].pseudo_patient_id == "BBB11"
    assert images_in_db[2].pseudo_patient_id == "CCC22"


def test_upload_with_no_participant_id(omop_resources: Path, db_session, mock_publisher) -> None:
    """
    GIVEN the database is empty,
    WHEN we parse a file with images that do not have participant_ids,
    THEN the database should have 3 images and the `pseudo_patient_id`s should be `None` in the
    database.
    """
    input_file = omop_resources / "batch_input.csv"
    messages_df = read_patient_info(input_file)
    messages = populate_queue_and_db(["imaging-primary"], messages_df, messages_priority=1)

    # Database has 3 rows now
    images_in_db: list[Image] = db_session.query(Image).all()
    assert len(images_in_db) == 3
    # A message per image
    assert len(messages) == 3
    # Pseudo_patient_id for new image is same as participant_ids in CSV file
    assert all(image.pseudo_patient_id is None for image in images_in_db)
