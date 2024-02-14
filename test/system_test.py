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
import time
from time import sleep

import pytest

pytest_plugins = "pytest_pixl"


@pytest.mark.usefixtures("_extract_radiology_reports")
def test_radiology_parquet():
    """
    scripts/check_radiology_parquet.py \
        ../exports/test-extract-uclh-omop-cdm/latest/radiology/radiology.parquet
    """


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
        time.sleep(2)
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
        SECONDS_WAIT = 5

        zip_files = []
        for seconds in range(0, 121, SECONDS_WAIT):
            zip_files = list(TestFtpsUpload.expected_output_dir.glob("*.zip"))
            logging.info("Waited for %s seconds. glob_list: %s", seconds, zip_files)
            if len(zip_files) == 2:
                break
            sleep(SECONDS_WAIT)

        # We expect 2 DICOM image studies to be uploaded
        assert len(zip_files) == 2


@pytest.mark.usefixtures("_setup_pixl_cli")
def test_orthanc_entries():
    """
    ./scripts/check_entry_in_orthanc_anon_for_2_min.py
    ./scripts/check_entry_in_pixl_anon.sh
    """


def test_max_storage_in_orthanc_raw():
    """
    This checks that orthanc-raw acknowledges the configured maximum storage size
    ./scripts/check_max_storage_in_orthanc_raw.sh
    Run this last because it will force out original test images from orthanc-raw
    ./scripts/check_max_storage_in_orthanc_raw.py
    """
