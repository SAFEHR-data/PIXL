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
import pathlib

import pytest
from core.database import Base, Extract, Image
from core.omop import OmopExtract
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(autouse=True)
def omop_files(tmp_path_factory: pytest.TempPathFactory, monkeypatch) -> OmopExtract:
    """
    Replace production extract instance with one writing to a tmpdir.

    :returns OmopExtract: For direct use when the fixture is explicity called.
    """
    export_dir = tmp_path_factory.mktemp("repo_base")
    tmpdir_extract = OmopExtract(export_dir)
    monkeypatch.setattr("pixl_cli._io.extract", tmpdir_extract)
    return tmpdir_extract


@pytest.fixture()
def resources() -> pathlib.Path:
    """Test resources directory path."""
    return pathlib.Path(__file__).parent / "resources"


@pytest.fixture(scope="module")
def monkeymodule():
    """Module level monkey patch."""
    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


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

    # super fun way to remove the schema name for sqlite
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(db_engine) -> Session:
    """
    Creates a session for uploading data to the in memory database.

    Will remove any committed data during teardown.

    :returns Session: Session for use in other setup fixtures.

    """
    InMemorySession = sessionmaker(db_engine)
    with InMemorySession() as session:
        # sqlite with sqlalchemy doesn't rollback, so manually deleting all database entities
        session.query(Image).delete()
        session.query(Extract).delete()
        yield session
    session.close()
