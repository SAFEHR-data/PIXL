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

import os
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytest_pixl.helpers import run_subprocess

if TYPE_CHECKING:
    import subprocess

# configure environmental variables
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["PIXL_DB_HOST"] = "localhost"
os.environ["PIXL_DB_PORT"] = "35432"
os.environ["PIXL_DB_NAME"] = "pixl"
os.environ["PIXL_DB_USER"] = "postgres"
os.environ["PIXL_DB_PASSWORD"] = "postgres"
os.environ["PROJECT_CONFIGS_DIR"] = str(Path(__file__).parents[2] / "projects/configs")

os.environ["ORTHANC_ANON_USERNAME"] = "orthanc_anon_username"
os.environ["ORTHANC_ANON_PASSWORD"] = "orthanc_anon_password"
os.environ["ORTHANC_ANON_URL"] = "http://orthanc-anon:8042"

TEST_DIR = Path(__file__).parent


@pytest.fixture(scope="package")
def run_containers() -> subprocess.CompletedProcess[bytes]:
    """Run docker containers for tests which require them."""
    yield run_subprocess(
        shlex.split("docker compose up --build --wait"),
        TEST_DIR,
        timeout=120,
    )
    run_subprocess(
        shlex.split("docker compose down --volumes"),
        TEST_DIR,
        timeout=60,
    )
