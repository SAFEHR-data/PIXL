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
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

import pytest
from core.db.models import Base, Extract, Image
from core.exports import ParquetExport
from core.upload import FTPSUploader
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from collections.abc import Generator

pytest_plugins = "pytest_pixl"

TEST_DIR = Path(__file__).parent
STUDY_DATE = datetime.date.fromisoformat("2023-01-01")

os.environ["RABBITMQ_USERNAME"] = "guest"
os.environ["RABBITMQ_PASSWORD"] = "guest"  # noqa: S105 Hardcoding password
os.environ["RABBITMQ_HOST"] = "localhost"
os.environ["RABBITMQ_PORT"] = "25672"
os.environ["PROJECT_CONFIGS_DIR"] = str(TEST_DIR.parents[1] / "project_configs")


@pytest.fixture(scope="package")
def run_containers() -> subprocess.CompletedProcess[bytes]:
    """Run docker containers for tests which require them."""
    subprocess.run(
        b"docker compose down --volumes",
        check=True,
        cwd=TEST_DIR,
        shell=True,  # noqa: S602
        timeout=60,
    )
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


class MockFTPSUploader(FTPSUploader):
    """Mock FTPSUploader for testing."""

    def __init__(self) -> None:
        """Initialise the mock uploader with hardcoded values for FTPS config."""
        self.host = "localhost"
        self.user = "pixl"
        self.password = "longpassword"  # noqa: S105 Hardcoding password
        self.port = 20021


@pytest.fixture()
def ftps_uploader() -> MockFTPSUploader:
    """Return a MockFTPSUploader object."""
    return MockFTPSUploader()


@pytest.fixture()
def ftps_home_dir(ftps_server) -> Generator[Path, None, None]:
    """
    Return the FTPS server home directory, the ftps_server fixture already uses
    pytest.tmp_path_factory, so no need to clean up.
    """
    return Path(ftps_server.home_dir)


@pytest.fixture()
def test_zip_content() -> BinaryIO:
    """Directory containing the test data for uploading to the ftp server."""
    test_zip_file = TEST_DIR / "data" / "public.zip"
    with test_zip_file.open("rb") as file_content:
        yield file_content


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


@pytest.fixture(autouse=True)
def export_dir(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """Tmp dir to for tests to extract to."""
    return tmp_path_factory.mktemp("export_base") / "exports"


@pytest.fixture()
def parquet_export(export_dir) -> ParquetExport:
    """Return a ParquetExport object."""
    return ParquetExport(
        project_name="i-am-a-project",
        extract_datetime=datetime.datetime.now(tz=datetime.timezone.utc),
        export_dir=export_dir,
    )
