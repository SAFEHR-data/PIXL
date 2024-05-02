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
"""Test functionality to upload files to an FTPS endpoint."""

import filecmp
import os
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from core.db.models import Image
from core.db.queries import update_exported_at
from core.exports import ParquetExport
from core.uploader._ftps import FTPSUploader
from pytest_pixl.plugin import FtpHostAddress

TEST_DIR = Path(__file__).parents[1]


class MockFTPSUploader(FTPSUploader):
    """Mock FTPSUploader for testing."""

    def __init__(self) -> None:
        """Initialise the mock uploader with hardcoded values for FTPS config."""
        self.host = os.environ["FTP_HOST"]
        self.user = os.environ["FTP_USER_NAME"]
        self.password = os.environ["FTP_PASSWORD"]
        self.port = int(os.environ["FTP_PORT"])


@pytest.fixture()
def ftps_uploader() -> MockFTPSUploader:
    """Return a MockFTPSUploader object."""
    return MockFTPSUploader()


@pytest.fixture()
def ftps_home_dir(ftps_server) -> Path:
    """
    Return the FTPS server home directory, the ftps_server fixture already uses
    pytest.tmp_path_factory, so no need to clean up.
    """
    return Path(ftps_server.home_dir)


@pytest.fixture(scope="session")
def ftp_host_address():
    """Run FTP on localhost - no docker containers need to access it"""
    return FtpHostAddress.LOCALHOST


@pytest.fixture()
def zip_content() -> Generator:
    """Directory containing the test data for uploading to the ftp server."""
    test_zip_file = TEST_DIR / "data" / "public.zip"
    with test_zip_file.open("rb") as file_content:
        yield file_content


@pytest.mark.usefixtures("ftps_server")
def test_send_via_ftps(
    zip_content, not_yet_exported_dicom_image, ftps_uploader, ftps_home_dir
) -> None:
    """Tests that DICOM image can be uploaded to the correct location"""
    # ARRANGE
    # Get the pseudo identifier from the test image
    pseudo_anon_id = not_yet_exported_dicom_image.hashed_identifier
    project_slug = "some-project-slug"
    expected_output_file = ftps_home_dir / project_slug / (pseudo_anon_id + ".zip")

    # ACT
    ftps_uploader.send_via_ftps(zip_content, pseudo_anon_id, project_slug)

    # ASSERT
    assert expected_output_file.exists()


def test_update_exported_and_save(rows_in_session) -> None:
    """Tests that the exported_at field is updated when a file is uploaded"""
    # ARRANGE
    expected_export_time = datetime.now(tz=timezone.utc)

    # ACT
    update_exported_at("not_yet_exported", expected_export_time)
    new_row = (
        rows_in_session.query(Image).filter(Image.hashed_identifier == "not_yet_exported").one()
    )
    actual_export_time = new_row.exported_at.replace(tzinfo=timezone.utc)

    # ASSERT
    assert actual_export_time == expected_export_time


@pytest.fixture()
def parquet_export(export_dir) -> ParquetExport:
    """
    Return a ParquetExport object.

    This fixture is deliberately not definied in conftest, because it imports the ParquetExport
    class, which in turn loads the PixlConfig class, which in turn requres the PROJECT_CONFIGS_DIR
    environment to be set. This environment variable is set in conftest, so the import needs to
    happen after that.
    """
    return ParquetExport(
        project_name_raw="i-am-a-project",
        extract_datetime=datetime.now(tz=timezone.utc),
        export_dir=export_dir,
    )


@pytest.mark.usefixtures("ftps_server")
def test_upload_parquet(parquet_export, ftps_home_dir, ftps_uploader) -> None:
    """Tests that parquet files are uploaded to the correct location (but ignore their contents)"""
    # ARRANGE

    parquet_export.copy_to_exports(Path(__file__).parents[3] / "test" / "resources" / "omop")
    parquet_export.export_radiology_linker(pd.DataFrame(list("dummy"), columns=["D"]))

    # ACT
    ftps_uploader.upload_parquet_files(parquet_export)

    # ASSERT
    expected_public_parquet_dir = (
        ftps_home_dir / parquet_export.project_slug / parquet_export.extract_time_slug / "parquet"
    )
    assert expected_public_parquet_dir.exists()

    # Print difference report to aid debugging (it doesn't actually assert anything)
    dc = filecmp.dircmp(parquet_export.current_extract_base, expected_public_parquet_dir)
    dc.report_full_closure()
    assert (
        expected_public_parquet_dir / "omop" / "public" / "PROCEDURE_OCCURRENCE.parquet"
    ).exists()
    assert (expected_public_parquet_dir / "radiology" / "IMAGE_LINKER.parquet").exists()


@pytest.mark.usefixtures("ftps_server")
def test_no_export_to_upload(parquet_export, ftps_uploader) -> None:
    """If there is nothing in the export directly, an exception is thrown"""
    parquet_export.public_output.mkdir(parents=True, exist_ok=True)
    with pytest.raises(FileNotFoundError):
        ftps_uploader.upload_parquet_files(parquet_export)
