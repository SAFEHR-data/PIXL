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

import pytest
import requests
from core.database import Base, Extract, Image
from dateutil.tz import UTC
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

STUDY_DATE = datetime.date.fromisoformat("2023-01-01")


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
    execution_options = {"schema_translate_map": {"pixl": None}}
    engine = create_engine(
        "sqlite:///:memory:",
        execution_options=execution_options,
        echo=True,
        echo_pool="debug",
        future=True,
    )
    monkeymodule.setattr("pixl_cli._database.engine", engine)

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


@pytest.fixture()
def return_hashed_val(requests_mock):
    requests_mock.get("http://test.com", text="f-i-x-e-d")
    response = requests.get("http://test.com").text
    assert response.status_code == 200
    return response.content


@pytest.fixture()
def dummy_env_var(monkeypatch):  # noqa: ANN202
    """Fixture to set up a dummy environment variables for hasher API"""
    monkeypatch.setenv("ENV", "testenv")
    monkeypatch.setenv("DEBUG", "True")
    monkeypatch.setenv("AZURE_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("AZURE_TENANT_ID", "test_tenant_id")
    monkeypatch.setenv("AZURE_KEY_VAULT_NAME", "test_AZ_KV_name")
    monkeypatch.setenv("AZURE_KEY_VAULT_SECRET_NAME", "test_AZ_KV_secret_name")
    monkeypatch.setenv("LOG_ROOT_DIR", "test_log_root_dir")
