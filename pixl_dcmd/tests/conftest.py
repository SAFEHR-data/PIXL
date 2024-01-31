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
"""CLI testing fixtures."""
from __future__ import annotations
import datetime
import os
import pytest
import requests
from core.db.models import Base, Extract, Image
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ["SALT_VALUE"] = "test_salt"
os.environ["HASHER_API_AZ_NAME"] = "test_hash_API"
os.environ["HASHER_API_PORT"] = "test_hash_API_port"
os.environ["TIME_OFFSET"] = "5"

STUDY_DATE = datetime.date.fromisoformat("2023-01-01")


@pytest.fixture()
def rows_in_session(db_session) -> Session:
    """Insert a test row for each table, returning the session for use in tests."""
    extract = Extract(slug="i-am-a-project")

    image_exported = Image(
        accession_number="AA12345601",
        study_date=STUDY_DATE,
        mrn="987654321",
        extract=extract,
        exported_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    image_not_exported = Image(
        accession_number="AA12345605",
        study_date=STUDY_DATE,
        mrn="987654321",
        extract=extract,
    )
    with db_session:
        db_session.add_all([extract, image_exported, image_not_exported])
        db_session.commit()

    return db_session


@pytest.fixture(scope="module")
def monkeymodule():
    """Module level monkey patch."""
    from _pytest.monkeypatch import MonkeyPatch

    monkeypatch = MonkeyPatch()
    yield monkeypatch
    monkeypatch.undo()


@pytest.fixture(autouse=True, scope="module")
def db_engine(monkeymodule) -> Engine:
    """
    Patches the database engine with an in memory database

    :returns Engine: Engine for use in other setup fixtures
    """
    # SQLite doesnt support schemas, so remove pixl schema from engine options
    execution_options = {"schema_translate_map": {"pipeline": None}}
    engine = create_engine(
        "sqlite:///:memory:",
        execution_options=execution_options,
        echo=True,
        echo_pool="debug",
        future=True,
    )
    monkeymodule.setattr("pixl_dcmd._database.engine", engine)

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(db_engine) -> Session:
    """
    Creates a session for interacting with an in memory database.

    Will remove any data from database in setup

    :returns Session: Session for use in other setup fixtures.

    """
    InMemorySession = sessionmaker(db_engine)
    with InMemorySession() as session:
        # sqlite with sqlalchemy doesn't rollback, so manually deleting all database entities
        session.query(Image).delete()
        session.query(Extract).delete()
        yield session
    session.close()


class MockResponse(object):
    def __init__(self, content: str):
        self.status_code = 200
        self.content = "-".join(list(content)).encode("utf-8")
        self.text = self.content.decode("utf-8")


# monkeypatched requests.get moved to a fixture
@pytest.fixture(autouse=True)
def mock_response(monkeypatch):
    """Requests.get() mocked to return MockedResponse built from input."""

    def mock_get(input: str):
        return MockResponse(input.split("=")[1])

    monkeypatch.setattr(requests, "get", mock_get)
