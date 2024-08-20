#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
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
from __future__ import annotations

import datetime
import os
import pathlib
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import requests
from core.db.models import Base, Extract, Image
from core.patient_queue.message import Message
from pydicom.uid import generate_uid
from pytest_pixl.helpers import run_subprocess
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Generator

pytest_plugins = "pytest_pixl"

TEST_DIR = Path(__file__).parent
STUDY_DATE = datetime.date.fromisoformat("2023-01-01")

os.environ["PIXL_MAX_MESSAGES_IN_FLIGHT"] = "10"
os.environ["RABBITMQ_USERNAME"] = "guest"
os.environ["RABBITMQ_PASSWORD"] = "guest"
os.environ["RABBITMQ_HOST"] = "localhost"
os.environ["RABBITMQ_PORT"] = "25672"
os.environ["PROJECT_CONFIGS_DIR"] = str(TEST_DIR.parents[1] / "projects/configs")

os.environ["FTP_HOST"] = "localhost"
os.environ["FTP_USER_NAME"] = "pixl"
os.environ["FTP_PASSWORD"] = "longpassword"
os.environ["FTP_PORT"] = "20021"

os.environ["ORTHANC_ANON_URL"] = "http://localhost:8043"
os.environ["ORTHANC_ANON_USERNAME"] = "orthanc"
os.environ["ORTHANC_ANON_PASSWORD"] = "orthanc"

os.environ["XNAT_HOST"] = "localhost"
os.environ["XNAT_USER_NAME"] = "pixl"
os.environ["XNAT_PASSWORD"] = "longpassword"
os.environ["XNAT_PORT"] = "8080"
os.environ["XNAT_DESTINATION"] = "/archive"
os.environ["XNAT_OVERWRITE"] = "none"


@pytest.fixture(scope="package")
def run_containers() -> Generator[subprocess.CompletedProcess[bytes], None, None]:
    """Run docker containers for tests which require them."""
    run_subprocess(
        shlex.split("docker compose down --volumes"),
        TEST_DIR,
        timeout=60,
    )
    yield run_subprocess(
        shlex.split("docker compose up --build --wait --remove-orphans"),
        TEST_DIR,
        timeout=60,
    )
    run_subprocess(
        shlex.split("docker compose down --volumes"),
        TEST_DIR,
        timeout=60,
    )


@pytest.fixture(scope="package")
def study_id(run_containers) -> str:
    """Uploads a DICOM file to the Orthanc server and returns the study ID."""
    DCM_FILE = Path(__file__).parents[2] / "test" / "resources" / "Dicom1.dcm"
    ORTHANC_ANON_URL = os.environ["ORTHANC_ANON_URL"]

    headers = {"content-type": "application/dicom"}
    data = DCM_FILE.read_bytes()
    response = requests.post(
        f"{ORTHANC_ANON_URL}/instances",
        data=data,
        headers=headers,
        auth=(os.environ["ORTHANC_ANON_USERNAME"], os.environ["ORTHANC_ANON_PASSWORD"]),
        timeout=60,
    )
    return response.json()["ParentStudy"]


@pytest.fixture(scope="module")
def monkeymodule():
    """Module level monkey patch."""
    from _pytest.monkeypatch import MonkeyPatch

    monkeypatch = MonkeyPatch()
    yield monkeypatch
    monkeypatch.undo()


@pytest.fixture(autouse=True, scope="module")
def db_engine(monkeymodule) -> Generator[Engine, None, None]:
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
    monkeymodule.setattr("core.db.queries.engine", engine)

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(db_engine) -> Generator[Session, None, None]:
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
def rows_in_session(db_session) -> Session:
    """Insert a test row for each table, returning the session for use in tests."""
    extract = Extract(slug="i-am-a-project")

    image_exported = Image(
        accession_number="123",
        study_date=STUDY_DATE,
        mrn="mrn",
        study_uid="1.2.3",
        extract=extract,
        exported_at=datetime.datetime.now(tz=datetime.timezone.utc),
        pseudo_study_uid=generate_uid(entropy_srcs=["already_exported"]),
    )
    image_not_exported = Image(
        accession_number="234",
        study_date=STUDY_DATE,
        mrn="mrn",
        study_uid="2.3.4",
        extract=extract,
        pseudo_study_uid=generate_uid(entropy_srcs=["not_yet_exported"]),
    )
    with db_session:
        db_session.add_all([extract, image_exported, image_not_exported])
        db_session.commit()

    return db_session


@pytest.fixture()
def not_yet_exported_dicom_image(rows_in_session) -> Image:
    """Return a DICOM image from the database."""
    return (
        rows_in_session.query(Image)
        .filter(Image.pseudo_study_uid == generate_uid(entropy_srcs=["not_yet_exported"]))
        .one()
    )


@pytest.fixture()
def already_exported_dicom_image(rows_in_session) -> Image:
    """Return a DICOM image from the database."""
    return (
        rows_in_session.query(Image)
        .filter(Image.pseudo_study_uid == generate_uid(entropy_srcs=["already_exported"]))
        .one()
    )


@pytest.fixture(autouse=True)
def export_dir(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """Tmp dir to for tests to extract to."""
    export_dir = tmp_path_factory.mktemp("export_base") / "exports"
    export_dir.mkdir()
    return export_dir


@pytest.fixture()
def mock_message() -> Message:
    """An example Message used for testing"""
    return Message(
        mrn="111",
        accession_number="123",
        study_uid="1.2.3",
        study_date=datetime.date.fromisoformat("2022-11-22"),
        procedure_occurrence_id="234",
        project_name="test project",
        extract_generated_timestamp=datetime.datetime.strptime(
            "Dec 7 2023 2:08PM", "%b %d %Y %I:%M%p"
        ).replace(tzinfo=datetime.timezone.utc),
        pseudo_patient_id="0"
    )