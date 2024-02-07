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
import shutil
import subprocess
from pathlib import Path
from typing import BinaryIO, Callable

import pytest
from core.db.models import Base, Extract, Image
from core.exports import ParquetExport
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


@pytest.fixture()
def resources() -> pathlib.Path:
    """Top-level test resources directory path."""
    return pathlib.Path(__file__).parents[2] / "test" / "resources"


@pytest.fixture()
def omop_es_batch_generator(resources, tmp_path_factory) -> Callable[..., pathlib.Path]:
    """
    return a callable which returns, by default, a path to (a copy of) the
    resources/omop/batch_1/ directory, as if it were a single batch.
    You can also set up any subset of the resources/omop/batch_* directories to be present
    in the returned directory. Useful for testing different setups without having a load of
    copied files in the resources/omop directory.
    """
    omop_batch_root = resources / "omop"
    # keep separate from a test that might want to use tmp_path
    tmp = tmp_path_factory.mktemp("copied_omop_es_input")

    def inner_gen(batches=None, *, single_batch: bool = True) -> pathlib.Path:
        if batches is None:
            batches = ["batch_1"]
        if single_batch:
            assert len(batches) == 1
            # the root tmp dir will already exist; we are effectively replacing it
            shutil.copytree(omop_batch_root / batches[0], tmp, dirs_exist_ok=True)
        else:
            assert batches
            for b in batches:
                shutil.copytree(omop_batch_root / b, tmp / b)
        return tmp

    return inner_gen


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
        capture_output=True,
    )
    subprocess.run(
        b"docker compose down --volumes",
        check=True,
        cwd=TEST_DIR,
        shell=True,  # noqa: S602
        timeout=60,
        capture_output=True,
    )


@pytest.fixture()
def test_zip_content() -> BinaryIO:
    """Directory containing the test data for uploading to the ftp server."""
    test_zip_file = TEST_DIR / "data" / "public.zip"
    with test_zip_file.open("rb") as file_content:
        yield file_content


@pytest.fixture()
def mounted_data(run_containers) -> Path:
    """
    The mounted data directory for the ftp server.
    This will contain the data after successful upload.
    Tear down through docker
    """
    yield MOUNTED_DATA_DIR
    # Tear down the directory after tests
    subprocess.run(
        b"docker compose exec ftp-server sh -c 'rm -r /home/pixl/*'",
        check=True,
        cwd=TEST_DIR,
        shell=True,  # noqa: S602
        timeout=60,
    ).check_returncode()


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
