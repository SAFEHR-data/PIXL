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
from core.database import Base, Extract, Image
from dateutil.tz import UTC
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

# os.environ["ENV"] = "test"
os.environ["SALT_VALUE"] = "salt"
os.environ["HASHER_API_AZ_NAME"] = "test_hash_API"
os.environ["HASHER_API_PORT"] = "test_hash_API_port"
os.environ["TIME_OFFSET"] = "5"
os.environ["DEBUG"] = "True"
os.environ["AZURE_CLIENT_ID"] = "test_client_id"
os.environ["AZURE_CLIENT_SECRET"] = "test_client_secret"
os.environ["AZURE_TENANT_ID"] = "test_tenant_id"
os.environ["AZURE_KEY_VAULT_NAME"] = "test_AZ_KV_name"
os.environ["AZURE_KEY_VAULT_SECRET_NAME"] = "test_AZ_KV_secret_name"
os.environ["LOG_ROOT_DIR"] = "test_log_root_dir"

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
        exported_at=datetime.datetime.now(tz=UTC),
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


def get_json(url):
    """Takes a URL, and returns the JSON."""
    r = requests.get(url)
    return r.json(), r.content


class MockResponse:
    def __init__(self):
        self.status_code = 200
        self.url = "www.testurl.com"
        self.content = "f-i-x-e-d"

    # mock json() method always returns a specific testing dictionary
    @staticmethod
    def json():
        return {"mock_key": "mock_response"}


# monkeypatched requests.get moved to a fixture
@pytest.fixture(autouse=True)
def mock_response(monkeypatch):
    """Requests.get() mocked to return {'mock_key':'mock_response'}."""

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests, "get", mock_get)


# @pytest.fixture(autouse=True)
# def mock_content(monkeypatch):
#     """Requests.get() mocked to return {'mock_key':'mock_response'}."""

#     def mock_get(*args, **kwargs):
#         return MockResponse().

#     monkeypatch.setattr(requests, "get", mock_get)


def test_get_json(monkeypatch):
    # app.get_json, which contains requests.get, uses the monkeypatch
    result = get_json(os.environ["HASHER_API_AZ_NAME"])
    assert result["mock_key"] == "mock_response"


# @pytest.fixture(autouse=True)
def request_mock_response(requests_mock):
    requests_mock.get(os.environ["HASHER_API_AZ_NAME"], text="f-i-x-e-d")
    response = requests.get(os.environ["HASHER_API_AZ_NAME"]).text
    assert response.status_code == 200
    return response.content


def test_get_response_success(monkeypatch):
    class MockResponse(object):
        def __init__(self):
            self.status_code = 200
            self.url = "http://httpbin.org/get"
            self.headers = {"foobar": "foooooo"}

        def json(self):
            return {"fooaccount": "foo123", "url": os.environ["HASHER_API_AZ_NAME"]}

    def mock_get(url):
        return MockResponse()

    monkeypatch.setattr(requests, "get", mock_get)


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
