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
import shutil
import subprocess
from pathlib import Path
from typing import BinaryIO

import pytest
from core.db.models import Base, Extract, Image
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ["RABBITMQ_USERNAME"] = "guest"
os.environ["RABBITMQ_PASSWORD"] = "guest"  # noqa: S105 Hardcoding password
os.environ["RABBITMQ_HOST"] = "localhost"
os.environ["RABBITMQ_PORT"] = "25672"
os.environ["FTP_HOST"] = "localhost"
os.environ["FTP_USER_NAME"] = "pixl"
os.environ["FTP_USER_PASSWORD"] = "longpassword"  # noqa: S105 Hardcoding password
os.environ["FTP_PORT"] = "20021"

TEST_DIR = Path(__file__).parent
MOUNTED_DATA_DIR = (
    Path(__file__).parents[2] / "test" / "dummy-services" / "ftp-server" / "mounts" / "data"
)
STUDY_DATE = datetime.date.fromisoformat("2023-01-01")


@pytest.fixture(scope="package")
def run_containers() -> subprocess.CompletedProcess[bytes]:
    """Run docker containers for tests which require them."""
    yield subprocess.run(
        b"docker compose up --build --wait",
        check=True,
        cwd=TEST_DIR,
        shell=True,  # noqa: S602
        timeout=60,
    )
    subprocess.run(
        b"docker compose down --volumes",
        check=True,
        cwd=TEST_DIR,
        shell=True,  # noqa: S602
        timeout=60,
    )


@pytest.fixture()
def test_zip_content() -> BinaryIO:
    """Directory containing the test data for uploading to the ftp server."""
    test_zip_file = TEST_DIR / "data" / "public.zip"
    with test_zip_file.open("rb") as file_content:
        yield file_content


@pytest.fixture()
def mounted_data() -> Path:
    """
    The mounted data directory for the ftp server.
    This will contain the data after successful upload.
    """
    yield MOUNTED_DATA_DIR
    sub_dirs = [f.path for f in os.scandir(MOUNTED_DATA_DIR) if f.is_dir()]
    # Tear down the directory after tests
    for sub_dir in sub_dirs:
        shutil.rmtree(sub_dir, ignore_errors=True)


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
    monkeymodule.setattr("core.db.queries.engine", engine)

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
def rows_in_session(db_session) -> Session:
    """Insert a test row for each table, returning the session for use in tests."""
    extract = Extract(slug="i-am-a-project")

    image_exported = Image(
        accession_number="123",
        study_date=STUDY_DATE,
        mrn="mrn",
        extract=extract,
        exported_at=datetime.datetime.now(tz=datetime.timezone.utc),
        hashed_identifier="already_exported",
    )
    image_not_exported = Image(
        accession_number="234",
        study_date=STUDY_DATE,
        mrn="mrn",
        extract=extract,
        hashed_identifier="not_yet_exported",
    )
    with db_session:
        db_session.add_all([extract, image_exported, image_not_exported])
        db_session.commit()

    return db_session


@pytest.fixture()
def not_yet_exported_dicom_image(rows_in_session) -> Image:
    """Return a DICOM image from the database."""
    return rows_in_session.query(Image).filter(Image.hashed_identifier == "not_yet_exported").one()


@pytest.fixture()
def already_exported_dicom_image(rows_in_session) -> Image:
    """Return a DICOM image from the database."""
    return rows_in_session.query(Image).filter(Image.hashed_identifier == "already_exported").one()
