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
"""System/E2E test setup"""
import logging
import subprocess
from pathlib import Path

import pytest

from pytest_pixl.plugin import FtpHostAddress
from utils import wait_for_stable_orthanc_anon

pytest_plugins = "pytest_pixl"


@pytest.fixture()
def host_export_root_dir():
    """Intermediate export dir as seen from the host"""
    return Path(__file__).parents[1] / "exports"


def run_subprocess(
    cmd: list[str], working_dir: Path, *, shell=False, timeout=360
) -> subprocess.CompletedProcess[bytes]:
    """
    Run a command but capture the stderr and stdout better than the CalledProcessError
    string representation does
    """
    try:
        logging.info("Running command %s", cmd)
        return subprocess.run(
            cmd,
            check=True,
            cwd=working_dir,
            shell=shell,  # noqa: S603 input is trusted
            timeout=timeout,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exception:
        logging.error("*** exception occurred running: '%s'", cmd)  # noqa: TRY400 will raise anyway
        logging.error("*** stdout:\n%s", exception.stdout.decode())  # noqa: TRY400
        logging.error("*** stderr:\n%s", exception.stderr.decode())  # noqa: TRY400
        raise


TEST_DIR = Path(__file__).parent
RESOURCES_DIR = TEST_DIR / "resources"
RESOURCES_OMOP_DIR = RESOURCES_DIR / "omop"


@pytest.fixture(scope="session")
def _setup_pixl_cli(ftps_server) -> None:
    """Run pixl populate/start. Cleanup intermediate export dir on exit."""
    # CLI calls need to have CWD = test dir so they can find the pixl_config.yml file
    run_subprocess(["pixl", "populate", str(RESOURCES_OMOP_DIR.absolute())], TEST_DIR)
    run_subprocess(["pixl", "start"], TEST_DIR)
    # poll here for two minutes to check for imaging to be processed, printing progress
    wait_for_stable_orthanc_anon(121, 5)
    yield
    run_subprocess(
        [
            "docker",
            "exec",
            "system-test-ehr-api-1",
            "rm",
            "-r",
            "/run/exports/test-extract-uclh-omop-cdm/",
        ],
        TEST_DIR,
    )


@pytest.fixture(scope="session")
def ftp_host_address():
    """Run FTP on docker host - docker containers do need to access it"""
    return FtpHostAddress.DOCKERHOST


@pytest.fixture(scope="session")
def _extract_radiology_reports(_setup_pixl_cli) -> None:
    """
    run pixl extract-radiology-reports.
    TODO: should then poll for two minutes to ensure that the database is populated,
     as per ./scripts/check_entry_in_pixl_anon.sh
    """
    run_subprocess(
        ["pixl", "extract-radiology-reports", str(RESOURCES_OMOP_DIR.absolute())], TEST_DIR
    )
