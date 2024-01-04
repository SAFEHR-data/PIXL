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

"""Test database interaction methods for the cli."""
import datetime

import pytest
from core.database import Extract, Image
from core.patient_queue.message import Message
from dateutil.tz import UTC
from pixl_cli._database import filter_exported_or_add_to_db
from sqlalchemy.orm import Session

STUDY_DATE = datetime.date.fromisoformat("2023-01-01")


def _make_message(project_name: str, accession_number: str, mrn: str) -> Message:
    return Message(
        project_name=project_name,
        accession_number=accession_number,
        mrn=mrn,
        study_date=STUDY_DATE,
        procedure_occurrence_id=1,
        omop_es_timestamp=datetime.datetime.now(tz=UTC),
    )


@pytest.fixture()
def example_messages():
    """Test input data."""
    return [
        _make_message(project_name="i-am-a-project", accession_number="123", mrn="mrn"),
        _make_message(project_name="i-am-a-project", accession_number="234", mrn="mrn"),
        _make_message(project_name="i-am-a-project", accession_number="345", mrn="mrn"),
    ]


@pytest.fixture()
def rows_in_session(db_session) -> Session:
    """Insert a test row for each table, returning the session for use in tests."""
    extract = Extract(slug="i-am-a-project")

    image_exported = Image(
        accession_number="123",
        study_date=STUDY_DATE,
        mrn="mrn",
        extract=extract,
        exported_at=datetime.datetime.now(tz=UTC),
    )
    image_not_exported = Image(
        accession_number="234",
        study_date=STUDY_DATE,
        mrn="mrn",
        extract=extract,
    )
    with db_session:
        db_session.add_all([extract, image_exported, image_not_exported])
        db_session.commit()

    return db_session


def test_project_doesnt_exist(example_messages, db_session):
    """If project doesn't exist, then no filtering of messages and then project saved to database"""
    output = filter_exported_or_add_to_db(example_messages, "i-am-a-project")
    assert output == example_messages


def test_first_image_exported(example_messages, rows_in_session):
    """
    GIVEN 3 messages, where one has been exported, the second has been saved to db but not exported
    WHEN the messages are filtered
    THEN the first message that has an exported_at value should not be in the filtered list
    """
    output = filter_exported_or_add_to_db(example_messages, "i-am-a-project")
    assert len(output) == len(example_messages) - 1
    assert [x for x in output if x.accession_number == "123"] == []
