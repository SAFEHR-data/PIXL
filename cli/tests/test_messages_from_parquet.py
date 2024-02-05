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
import os
import shutil

import pytest
from core.patient_queue.message import Message
from pixl_cli._io import (
    copy_parquet_return_logfile_fields,
    determine_batch_structure,
    messages_from_parquet,
)
from pyarrow import ArrowException


@pytest.mark.parametrize(
    ("batches", "single_batch", "expected_message_indexes"),
    [
        (["batch_1", "batch_2"], False, [0, 1]),
        (["batch_1"], True, [0]),
        (["batch_1"], False, [0]),
        (["batch_2"], True, [1]),
        (["batch_2"], False, [1]),
    ],
)
def test_messages_from_parquet(
    omop_es_batch_generator, batches, single_batch, expected_message_indexes
) -> None:
    """
    Given a valid OMOP ES extract with 4 procedures, two of which are x-rays.
    When the messages are generated from the directory and the output of logfile parsing
    Then two messages should be generated
    """
    # Arrange
    omop_parquet_dir = omop_es_batch_generator(batches, single_batch=single_batch)
    project_name, omop_es_datetime, batch_dirs = copy_parquet_return_logfile_fields(
        omop_parquet_dir
    )
    # Act
    messages = []
    for batch in batch_dirs:
        messages.extend(messages_from_parquet(batch, project_name, omop_es_datetime))
    # Assert
    assert all(isinstance(msg, Message) for msg in messages)

    all_expected_messages = [
        Message(
            mrn="987654321",
            accession_number="AA12345601",
            study_date=datetime.date.fromisoformat("2020-05-23"),
            procedure_occurrence_id=4,
            project_name="test-extract-uclh-omop-cdm",
            omop_es_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
        Message(
            mrn="987654321",
            accession_number="AA12345605",
            study_date=datetime.date.fromisoformat("2020-05-23"),
            procedure_occurrence_id=5,
            project_name="test-extract-uclh-omop-cdm",
            omop_es_timestamp=datetime.datetime.fromisoformat("2023-12-07T14:08:58"),
        ),
    ]
    expected_messages = [all_expected_messages[i] for i in expected_message_indexes]
    assert messages == expected_messages


def test_conflicting_batches(omop_es_batch_generator) -> None:
    """
    Batches 1 and 3 have different timestamps so should fail if they are given to us as part of the
    same extract.
    """
    omop_parquet_dir = omop_es_batch_generator(["batch_1", "batch_3"], single_batch=False)
    with pytest.raises(RuntimeError, match=r"log files with different IDs.*batch_.*batch_"):
        copy_parquet_return_logfile_fields(omop_parquet_dir)


def test_empty_batches(tmp_path) -> None:
    """Empty dir, nothing found."""
    with pytest.raises(RuntimeError, match=r"No batched or unbatched log files found in"):
        copy_parquet_return_logfile_fields(tmp_path)


def test_missing_public(omop_es_batch_generator) -> None:
    """
    This error is hard to reach in real life because a missing public dir would trigger an error
    from copy_parquet_return_logfile_fields first.
    """
    omop_parquet_dir = omop_es_batch_generator(["batch_1"], single_batch=True)
    # simulate broken input batch
    shutil.rmtree(omop_parquet_dir / "public", ignore_errors=False)

    project_name, omop_es_datetime, batch_dirs = determine_batch_structure(omop_parquet_dir)
    with pytest.raises(NotADirectoryError):
        messages_from_parquet(omop_parquet_dir, project_name, omop_es_datetime)


@pytest.mark.parametrize(
    "file_to_corrupt",
    [
        # include all parquet files required to generate messages
        "public/PROCEDURE_OCCURRENCE.parquet",
        "private/PROCEDURE_OCCURRENCE_LINKS.parquet",
        "private/PERSON_LINKS.parquet",
    ],
)
def test_broken_parquet_dir(omop_es_batch_generator, file_to_corrupt) -> None:
    """
    Check that if any of the parquet files we use to generate messages are incomplete,
    nothing much happens. We aren't checking the validity of parquet files that we simply copy
    to the extract dir.
    We fail even if batch_1 is fine but batch_2 is faulty; this might be an argument
    for continuing to call messages_from_parquet on *all* batches before sending any messages,
    as long as that's not too slow or uses too much memory.
    """
    omop_parquet_dir = omop_es_batch_generator(["batch_1", "batch_2"], single_batch=False)
    # Assume most likely error is an incomplete copy. Because parquet has a magic footer,
    # even one byte missing at the end should be enough for it to fail.
    to_corrupt = omop_parquet_dir / "batch_2" / file_to_corrupt
    new_size = to_corrupt.stat().st_size - 1
    os.truncate(to_corrupt, new_size)
    project_name, omop_es_datetime, batch_dirs = determine_batch_structure(omop_parquet_dir)
    with pytest.raises(ArrowException):  # noqa: PT012 It may not fail on all, but must fail on one
        for b in batch_dirs:
            messages_from_parquet(b, project_name, omop_es_datetime)
