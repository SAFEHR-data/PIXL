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

import pathlib
import shutil
from typing import TYPE_CHECKING

import pytest
from core.db.models import Base, Extract, Image
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture(autouse=True)
def export_dir(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """Tmp dir to for tests to extract to."""
    return tmp_path_factory.mktemp("export_base") / "exports"


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
