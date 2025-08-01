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

from collections.abc import Generator
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pydicom
import pytest
import requests
from loguru import logger
from pydicom.uid import UID
from pytest_check import check
from pytest_pixl.ftpserver import PixlFTPServer
from pytest_pixl.helpers import run_subprocess, wait_for_condition

pytest_plugins = "pytest_pixl"

SECONDS_TO_WAIT_FOR_CONDITION = 251


@pytest.fixture
def expected_studies() -> dict[int, dict]:
    """Expected study metadata post-anonymisation."""
    return {
        4: {
            "original_study_instance_uid": "1.3.46.670589.11.38023.5.0.14068.2023012517090160001",
            "instances": {
                # tuple made up of (AccessionNumber, SeriesDescription)
                # for AA12345601
                ("ANONYMIZED", "include123"),
                ("ANONYMIZED", "AP"),
            },
        },
        5: {
            "original_study_instance_uid": "1.3.46.670589.11.38023.5.0.14068.2023012517090160002",
            "instances": {
                # for AA12345605,
                ("ANONYMIZED", "include123"),
            },
        },
    }


@pytest.fixture
def expected_instances_for_series_querying(request: pytest.FixtureRequest) -> set[tuple[str, str]]:
    """Expected study metadata post-anonymisation when querying at the Series level."""
    # tuple made up of (AccessionNumber, SeriesDescription)
    # for AA12345601
    instances = {
        "single-series": {
            ("ANONYMIZED", "AP"),
        },
        "all-series": {
            ("ANONYMIZED", "AP"),
            ("ANONYMIZED", "include123"),
        },
    }
    return instances[request.param]


class TestFtpsUpload:
    """tests adapted from ./scripts/check_ftps_upload.py"""

    # Shared test data for the two different kinds of FTP upload test
    ftp_home_dir: Path
    project_slug: str
    extract_time_slug: str
    expected_output_dir: Path
    expected_public_parquet_dir: Path

    @pytest.fixture(scope="class", autouse=True)
    def _setup(self, ftps_server: PixlFTPServer) -> Generator:
        """Shared test data for the two different kinds of FTP upload test"""
        TestFtpsUpload.ftp_home_dir = ftps_server.home_dir
        logger.info("ftp home dir: {}", TestFtpsUpload.ftp_home_dir)

        TestFtpsUpload.project_slug = "test-extract-uclh-omop-cdm"
        TestFtpsUpload.extract_time_slug = "2023-12-07t14-08-58"

        TestFtpsUpload.expected_output_dir = (
            TestFtpsUpload.ftp_home_dir / TestFtpsUpload.project_slug
        )
        TestFtpsUpload.expected_public_parquet_dir = (
            TestFtpsUpload.expected_output_dir / TestFtpsUpload.extract_time_slug / "parquet"
        )
        logger.info("expected output dir: {}", TestFtpsUpload.expected_output_dir)
        logger.info("expected parquet files dir: {}", TestFtpsUpload.expected_public_parquet_dir)

        yield

        # cleanup export directory as other tests use the same FTPS server and export directory
        zip_files = list(TestFtpsUpload.expected_output_dir.glob("*.zip"))
        for z in zip_files:
            logger.info("Removing zip file: {}", z)
            z.unlink()

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
    def test_ftps_radiology_linker_upload(self, expected_studies: dict) -> None:
        """The generated radiology linker file"""
        radiology_linker_data = pd.read_parquet(
            TestFtpsUpload.expected_public_parquet_dir / "radiology" / "IMAGE_LINKER.parquet"
        )
        po_col = radiology_linker_data["procedure_occurrence_id"]
        for procedure_occurrence_id, studies in expected_studies.items():
            expected_po_id = procedure_occurrence_id
            row = radiology_linker_data[po_col == expected_po_id].iloc[0]
            assert UID(row.pseudo_study_uid).is_valid
            assert row.pseudo_study_uid != studies["original_study_instance_uid"]

        assert radiology_linker_data.shape[0] == 2
        assert set(radiology_linker_data.columns) == {
            "procedure_occurrence_id",
            "pseudo_study_uid",
        }

    @pytest.mark.usefixtures("_export_patient_data")
    def test_ftps_dicom_upload(
        self, tmp_path_factory: pytest.TempPathFactory, expected_studies: dict
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
            seconds_max=SECONDS_TO_WAIT_FOR_CONDITION,
            seconds_interval=5,
            seconds_condition_stays_true_for=15,
            progress_string_fn=zip_file_list,
        )
        assert zip_files
        radiology_linker_data = pd.read_parquet(
            TestFtpsUpload.expected_public_parquet_dir / "radiology" / "IMAGE_LINKER.parquet"
        )
        radiology_linker_data = radiology_linker_data.set_index("pseudo_study_uid")
        for z in zip_files:
            unzip_dir = tmp_path_factory.mktemp("unzip_dir", numbered=True)
            procedure = radiology_linker_data.loc[z.stem]["procedure_occurrence_id"]
            logger.info("Checking tags in zip file {} for procedure {}", z, procedure)
            self._check_dcm_tags_from_zip(z, unzip_dir, expected_studies[procedure])

    def _check_dcm_tags_from_zip(
        self, zip_path: Path, unzip_dir: Path, expected_study: dict
    ) -> None:
        """Check that private tag has survived anonymisation with the correct value."""
        run_subprocess(
            ["unzip", zip_path],
            working_dir=unzip_dir,
        )
        dicom_in_zip = list(unzip_dir.rglob("*.dcm"))

        # One zip file == one study.
        # There can be multiple instances in the zip file, one per file
        logger.info("In zip file, {} DICOM files: {}", len(dicom_in_zip), dicom_in_zip)
        actual_instances = set()
        for dcm_file in dicom_in_zip:
            dcm = pydicom.dcmread(dcm_file)
            # The actual dicom filename and dir structure isn't checked - should it be?
            assert (
                dcm.get("StudyInstanceUID") == zip_path.stem
            )  # StudyInstanceUID stores the pseudo study id post anon
            actual_instances.add((dcm.get("AccessionNumber"), dcm.get("SeriesDescription")))
        # check the basic info about the instances exactly matches
        with check:
            assert actual_instances == expected_study["instances"]


@pytest.mark.parametrize(
    ("_setup_pixl_cli_series", "expected_instances_for_series_querying"),
    [
        ("single-series.csv", "single-series"),
        ("all-series.csv", "all-series"),
    ],
    indirect=True,
)
@pytest.mark.usefixtures("_setup_pixl_cli_series")
def test_ftps_series_querying(
    ftps_server: PixlFTPServer, expected_instances_for_series_querying: set[tuple[str, str]]
) -> None:
    """Test querying at the Series level and check that only the requested instances are present."""
    expected_output_dir = ftps_server.home_dir / "test-extract-uclh-omop-cdm"
    zip_files: list[Path] = []

    def zip_file_list() -> str:
        return f"zip files found: {zip_files}"

    def one_zip_files_present() -> bool:
        nonlocal zip_files
        zip_files = list(expected_output_dir.glob("*.zip"))
        # We expect 1 study to be uploaded
        return len(zip_files) == 1

    wait_for_condition(
        one_zip_files_present,
        seconds_max=SECONDS_TO_WAIT_FOR_CONDITION,
        seconds_interval=5,
        seconds_condition_stays_true_for=15,
        progress_string_fn=zip_file_list,
    )

    zip_file = zip_files[0]
    actual_instances = set()
    with ZipFile(zip_file, "r") as zipped_study:
        for file_info in zipped_study.infolist():
            with zipped_study.open(file_info) as file:
                dataset = pydicom.dcmread(file)
                actual_instances.add(
                    (dataset.get("AccessionNumber"), dataset.get("SeriesDescription"))
                )
    with check:
        assert len(actual_instances) == len(expected_instances_for_series_querying)
        assert actual_instances == expected_instances_for_series_querying


@pytest.mark.usefixtures("_setup_pixl_cli_dicomweb")
def test_dicomweb_upload() -> None:
    """Check upload to DICOMweb server was successful"""
    # This should point to the dicomweb server, as seen from the local host machine
    LOCAL_DICOMWEB_URL = "http://localhost:8044"

    dicomweb_studies: list[str] = []

    def dicomweb_studies_list() -> str:
        return f"DICOMweb studies found: {dicomweb_studies}"

    def two_studies_present_on_dicomweb() -> bool:
        nonlocal dicomweb_studies
        response = requests.get(
            LOCAL_DICOMWEB_URL + "/studies",
            auth=("orthanc_dicomweb", "orthanc_dicomweb"),
            timeout=30,
        )
        dicomweb_studies = response.json()
        return len(dicomweb_studies) == 2

    wait_for_condition(
        two_studies_present_on_dicomweb,
        seconds_max=SECONDS_TO_WAIT_FOR_CONDITION,
        seconds_interval=10,
        progress_string_fn=dicomweb_studies_list,
    )
