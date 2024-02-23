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
"""Replacement for the 'interesting' bits of the system/E2E test"""
import logging
from pathlib import Path

import pytest
from pytest_pixl.helpers import run_subprocess, wait_for_condition

pytest_plugins = "pytest_pixl"


class TestFtpsUpload:
    """tests adapted from ./scripts/check_ftps_upload.py"""

    @pytest.fixture(scope="class", autouse=True)
    def _setup(self, ftps_server) -> None:
        """Shared test data for the two different kinds of FTP upload test"""
        TestFtpsUpload.ftp_home_dir = ftps_server.home_dir
        logging.info("ftp home dir: %s", TestFtpsUpload.ftp_home_dir)

        TestFtpsUpload.project_slug = "test-extract-uclh-omop-cdm"
        TestFtpsUpload.extract_time_slug = "2023-12-07t14-08-58"

        TestFtpsUpload.expected_output_dir = (
            TestFtpsUpload.ftp_home_dir / TestFtpsUpload.project_slug
        )
        TestFtpsUpload.expected_public_parquet_dir = (
            TestFtpsUpload.expected_output_dir / TestFtpsUpload.extract_time_slug / "parquet"
        )
        logging.info("expected output dir: %s", TestFtpsUpload.expected_output_dir)
        logging.info("expected parquet files dir: %s", TestFtpsUpload.expected_public_parquet_dir)
        # No cleanup of ftp uploads needed because it's in a temp dir

    @pytest.mark.usefixtures("_extract_radiology_reports")
    def test_ftps_parquet_upload(self):
        """The copied parquet files"""
        assert TestFtpsUpload.expected_public_parquet_dir.exists()

        assert (
            TestFtpsUpload.expected_public_parquet_dir
            / "omop"
            / "public"
            / "PROCEDURE_OCCURRENCE.parquet"
        ).exists()
        assert (
            TestFtpsUpload.expected_public_parquet_dir / "radiology" / "radiology.parquet"
        ).exists()

    @pytest.mark.usefixtures("_extract_radiology_reports")
    def test_ftps_dicom_upload(self):
        """Test whether DICOM images have been uploaded"""
        zip_files = []

        def zip_file_list() -> str:
            return f"zip files found: {zip_files}"

        def two_zip_files_present() -> bool:
            nonlocal zip_files
            zip_files = list(TestFtpsUpload.expected_output_dir.glob("*.zip"))
            # We expect 2 DICOM image studies to be uploaded
            return len(zip_files) == 2

        wait_for_condition(
            two_zip_files_present,
            seconds_max=121,
            seconds_interval=5,
            progress_string_fn=zip_file_list,
        )


@pytest.mark.usefixtures("_setup_pixl_cli")
def test_ehr_anon_entries():
    """Check data has reached ehr_anon."""

    def exists_two_rows() -> bool:
        # This was converted from old shell script - better to check more than just row count?
        sql_command = "select * from emap_data.ehr_anon"
        cp = run_subprocess(
            [
                "docker",
                "exec",
                "system-test-postgres-1",
                "/bin/bash",
                "-c",
                f'PGPASSWORD=pixl_db_password psql -U pixl_db_username -d pixl -c "{sql_command}"',
            ],
            Path.cwd(),
        )
        return cp.stdout.decode().find("(2 rows)") != -1

    # We already waited in _setup_pixl_cli, so should be true immediately.
    wait_for_condition(exists_two_rows)
