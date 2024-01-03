"""Dummy test stub to ensure that test database is set up correctly. Will remove."""
import datetime

import pytest
from core.database import Extract, Image
from core.patient_queue.message import Message
from dateutil.tz import UTC
from pixl_cli._database import _number_of_images, filter_if_exported
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
    """Insert some a test row for each table, returning the session for use in tests."""
    extract = Extract(slug="i-am-a-project")

    image = Image(
        accession_number="123",
        study_date=STUDY_DATE,
        mrn="mrn",
        extract=extract,
        exported_at=datetime.datetime.now(tz=UTC),
    )
    with db_session:
        db_session.add(extract)
        db_session.add(image)
        db_session.commit()

    return db_session


def test_no_data():
    """Ensure no data exists before load."""
    assert _number_of_images() == 0


def test_rows(rows_in_session):
    """Test images added from fixture."""
    assert _number_of_images() == 1


def test_project_doesnt_exist(example_messages, db_session):
    """If project doesn't exist, then no filtering of messages and then project saved to database"""
    output = filter_if_exported(example_messages, "i-am-a-project")
    assert output == example_messages


def test_first_image_exported(example_messages, rows_in_session):
    """If one message has been exported from test messages, that should be filtered out."""
    output = filter_if_exported(example_messages, "i-am-a-project", rows_in_session)
    assert len(output) == len(example_messages) - 1
    assert [x for x in output if x.accession_number == "123"] == []
