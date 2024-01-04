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

import pytest
from core.omop import OmopExtract


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
