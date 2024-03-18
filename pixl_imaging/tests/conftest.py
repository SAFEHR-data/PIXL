"""Setup for tests."""
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

import os
import shlex
import subprocess
from collections.abc import Generator
from logging import getLogger
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch
from pytest_pixl.helpers import run_subprocess

logger = getLogger(__name__)

os.environ["TEST"] = "true"
os.environ["LOGLEVEL"] = "DEBUG"
os.environ["RABBITMQ_PASSWORD"] = "guest"
os.environ["RABBITMQ_USERNAME"] = "guest"
os.environ["RABBITMQ_HOST"] = "queue"
os.environ["RABBITMQ_PORT"] = "5672"
os.environ["ORTHANC_RAW_URL"] = "http://localhost:8044"
os.environ["ORTHANC_RAW_USERNAME"] = "orthanc"
os.environ["ORTHANC_RAW_PASSWORD"] = "orthanc"
os.environ["ORTHANC_RAW_AE_TITLE"] = "PIXLRAW"
os.environ["ORTHANC_VNA_URL"] = "http://localhost:8043"
os.environ["ORTHANC_VNA_USERNAME"] = "orthanc"
os.environ["ORTHANC_VNA_PASSWORD"] = "orthanc"
os.environ["ORTHANC_VNA_AE_TITLE"] = "VNAQR"
os.environ["VNAQR_MODALITY"] = "UCVNAQR"
os.environ["PIXL_DICOM_TRANSFER_TIMEOUT"] = "30"
os.environ["SKIP_ALEMBIC"] = "true"
os.environ["PIXL_MAX_MESSAGES_IN_FLIGHT"] = "20"
os.environ["ORTHANC_AUTOROUTE_RAW_TO_ANON"] = "false"


@pytest.fixture(autouse=True)
def _patch_send_existing_study_to_anon(monkeypatch: Generator[MonkeyPatch, None, None]) -> None:
    """Patch send_existing_study_to_anon in Orthanc as orthanc raw doesn't use the pixl plugin."""

    def patched_send(self, resource_id: str) -> None:
        """Replaces send_existing_study_to_anon."""
        logger.info("Intercepted request to send '%s' to anon", resource_id)

    monkeypatch.setattr("pixl_imaging._orthanc.Orthanc.send_existing_study_to_anon", patched_send)


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