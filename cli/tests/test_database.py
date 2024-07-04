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
from core.db.models import Extract, Image
from core.patient_queue.message import Message
from pixl_cli._database import exported_images_for_project, filter_exported_or_add_to_db
from sqlalchemy.orm import Session

STUDY_DATE = datetime.date.fromisoformat("2023-01-01")


def _make_message(project_name: str, accession_number: str, mrn: str) -> Message:
    return Message(
        project_name=project_name,
        accession_number=accession_number,
        mrn=mrn,
        study_date=STUDY_DATE,
        procedure_occurrence_id=1,
        extract_generated_timestamp=datetime.datetime.now(tz=datetime.UTC),
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
        exported_at=datetime.datetime.now(tz=datetime.UTC),
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
    """If project doesn't exist, no filtering and then project & messages saved to database"""
    output = filter_exported_or_add_to_db(example_messages, "i-am-a-project")
    assert output == example_messages
    extract = db_session.query(Extract).one()
    images = db_session.query(Image).filter(Image.extract == extract).all()
    assert len(images) == len(example_messages)


def test_first_image_exported(example_messages, rows_in_session):
    """
    GIVEN 3 messages, where one has been exported, the second has been saved to db but not exported
    WHEN the messages are filtered
    THEN the first message that has an exported_at value should not be in the filtered list
        and all images should be saved to the database
    """
    output = filter_exported_or_add_to_db(example_messages, "i-am-a-project")
    assert len(output) == len(example_messages) - 1
    assert [x for x in output if x.accession_number == "123"] == []
    extract = rows_in_session.query(Extract).one()
    images = rows_in_session.query(Image).filter(Image.extract == extract).all()
    assert len(images) == len(example_messages)


def test_new_extract_with_overlapping_images(example_messages, rows_in_session):
    """
    GIVEN messages from a new extract, two have been saved to the database with another extract
    WHEN the messages are filtered
    THEN all messages should be returned and all new images should be added
    """
    new_project_name = "new-project"
    for message in example_messages:
        message.project_name = new_project_name

    output = filter_exported_or_add_to_db(example_messages, new_project_name)

    # none filtered out
    assert len(output) == len(example_messages)
    # all new batch of images saved
    extract = rows_in_session.query(Extract).filter(Extract.slug == new_project_name).one()
    images = rows_in_session.query(Image).filter(Image.extract == extract).all()
    assert len(images) == len(example_messages)
    # other extract and images still in database
    assert len(rows_in_session.query(Extract).all()) > 1
    assert len(rows_in_session.query(Image).all()) > len(example_messages)


def test_processed_images_for_project(rows_in_session):
    """
    GIVEN a project with 3 images in the database, only one of which is exported
    WHEN the processed_images_for_project function is called
    THEN only the exported images are returned
    """
    processed = exported_images_for_project("i-am-a-project")
    assert len(processed) == 1
    assert processed[0].accession_number == "123"
