"""Dummy test stub to ensure that test database is set up correctly. Will remove."""
import datetime

import pytest
from core.database import Extract, Image
from dateutil.tz import UTC
from pixl_cli._database import _number_of_images
from sqlalchemy.orm import Session


@pytest.fixture()
def rows_in_session(db_session) -> Session:
    """Insert some a test row for each table, returning the session for use in tests."""
    extract = Extract(slug="i-am-a-project")

    image = Image(
        accession_number="123",
        study_date=datetime.datetime.now(tz=UTC).date(),
        mrn="mrn",
        extract=extract,
    )
    with db_session.begin():
        db_session.add(extract)
        db_session.add(image)
    return db_session


def test_no_data():
    """Ensure no data exists before load."""
    assert _number_of_images() == 0


def test_rows(rows_in_session):  # noqa: ARG001
    """Test images added from fixture."""
    assert _number_of_images() == 1
