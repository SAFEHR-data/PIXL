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

import pandas as pd
import pydicom
import pytest
from core.dicom_tags import DICOM_TAG_PROJECT_NAME
from pytest_pixl.ftpserver import PixlFTPServer
from pytest_pixl.helpers import run_subprocess, wait_for_condition

pytest_plugins = "pytest_pixl"


@pytest.fixture()
def expected_studies():
    return {
        "d40f0639105babcdec043f1acf7330a8ebd64e64f13f7d0d4745f0135ddee0cd": {
            "procedure_occurrence_id": 4,
            "instances": {
                # tuple made up of (AccessionNumber, SeriesDescription)
                # for AA12345601
                ("ANONYMIZED", "include123"),
                ("ANONYMIZED", "AP"),
            },
        },
        "7ff25b0b438d23a31db984f49b0d6ca272104eb3d20c82f30e392cff5446a9c3": {
            "procedure_occurrence_id": 5,
            "instances": {
                # for AA12345605,
                ("ANONYMIZED", "include123"),
            },
        },
    }


class TestFtpsUpload:
    """tests adapted from ./scripts/check_ftps_upload.py"""

    # Shared test data for the two different kinds of FTP upload test
    ftp_home_dir: Path
    project_slug: str
    extract_time_slug: str
    expected_output_dir: Path
    expected_public_parquet_dir: Path

    @pytest.fixture(scope="class", autouse=True)
    def _setup(self, ftps_server: PixlFTPServer) -> None:
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

    @pytest.mark.usefixtures("_export_patient_data")
    def test_ftps_parquet_upload(self) -> None:
        """The copied parquet files"""
        assert TestFtpsUpload.expected_public_parquet_dir.exists()

        assert (
            TestFtpsUpload.expected_public_parquet_dir
            / "omop"
            / "public"
            / "PROCEDURE_OCCURRENCE.parquet"
        ).exists()

    @pytest.mark.usefixtures("_export_patient_data")
    def test_ftps_radiology_linker_upload(self, expected_studies) -> None:
        """The generated radiology linker file"""
        assert (
            TestFtpsUpload.expected_public_parquet_dir / "radiology" / "IMAGE_LINKER.parquet"
        ).exists()

        radiology_linker_data = pd.read_parquet(
            TestFtpsUpload.expected_public_parquet_dir / "radiology" / "IMAGE_LINKER.parquet"
        )
        po_col = radiology_linker_data["procedure_occurrence_id"]
        for study_id, studies in expected_studies.items():
            expected_po_id = studies["procedure_occurrence_id"]
            row = radiology_linker_data[po_col == expected_po_id].iloc[0]
            assert row.hashed_identifier == study_id

        assert radiology_linker_data.shape[0] == 2
        assert set(radiology_linker_data.columns) == {
            "procedure_occurrence_id",
            "hashed_identifier",
        }

    @pytest.mark.usefixtures("_export_patient_data")
    def test_ftps_dicom_upload(
        self, tmp_path_factory: pytest.TempPathFactory, expected_studies
    ) -> None:
        """Test whether DICOM images have been uploaded"""
        zip_files: list[Path] = []

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
            seconds_condition_stays_true_for=15,
            progress_string_fn=zip_file_list,
        )
        assert zip_files
        for z in zip_files:
            unzip_dir = tmp_path_factory.mktemp("unzip_dir", numbered=True)
            self._check_dcm_tags_from_zip(z, unzip_dir, expected_studies)

    def _check_dcm_tags_from_zip(
        self, zip_path: Path, unzip_dir: Path, expected_studies: dict[str, set[tuple[str, str]]]
    ) -> None:
        """Check that private tag has survived anonymisation with the correct value."""
        expected_instances = expected_studies[zip_path.stem]["instances"]
        run_subprocess(
            ["unzip", zip_path],
            working_dir=unzip_dir,
        )
        dicom_in_zip = list(unzip_dir.rglob("*.dcm"))

        # One zip file == one study.
        # There can be multiple instances in the zip file, one per file
        logging.info("In zip file, %s DICOM files: %s", len(dicom_in_zip), dicom_in_zip)
        actual_instances = set()
        for dcm_file in dicom_in_zip:
            dcm = pydicom.dcmread(dcm_file)
            # The actual dicom filename and dir structure isn't checked - should it be?
            assert dcm.get("PatientID") == zip_path.stem  # PatientID stores study id post anon
            actual_instances.add((dcm.get("AccessionNumber"), dcm.get("SeriesDescription")))
            block = dcm.private_block(
                DICOM_TAG_PROJECT_NAME.group_id, DICOM_TAG_PROJECT_NAME.creator_string
            )
            tag_offset = DICOM_TAG_PROJECT_NAME.offset_id
            private_tag = block[tag_offset]
            assert private_tag is not None
            if isinstance(private_tag.value, bytes):
                # Allow this for the time being, until it has been investigated
                # See https://github.com/UCLH-Foundry/PIXL/issues/363
                logging.error(
                    "TEMPORARILY IGNORE: tag value %s should be of type str, but is of type bytes",
                    private_tag.value,
                )
                assert private_tag.value.decode() == TestFtpsUpload.project_slug
            else:
                assert private_tag.value == TestFtpsUpload.project_slug
        # check the basic info about the instances exactly matches
        assert actual_instances == expected_instances
