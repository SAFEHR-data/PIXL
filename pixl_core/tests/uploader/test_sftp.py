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
"""Test uploading files to an SFTP endpoint."""

import filecmp
import os
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from core.db.models import Image
from core.db.queries import update_exported_at
from core.exports import ParquetExport
from core.uploader._sftp import SFTPUploader
from pixl_core.tests.uploader.helpers.sftpserver import SFTPServer
from pydicom.uid import generate_uid

TEST_DIR = Path(__file__).parents[1]
SFTP_UPLOAD_DIR = "upload"

os.environ["SFTP_HOST"] = "localhost"
os.environ["SFTP_USERNAME"] = "testuser"
os.environ["SFTP_PASSWORD"] = "testpass"
os.environ["SFTP_PORT"] = "2222"


class MockSFTPUploader(SFTPUploader):
    """Mock SFTPUploader for testing."""

    def __init__(self, known_hosts_path: Path) -> None:
        """Initialise the mock uploader with hardcoded values for SFTP config."""
        self.host = os.environ["SFTP_HOST"]
        self.username = os.environ["SFTP_USERNAME"]
        self.password = os.environ["SFTP_PASSWORD"]
        self.port = int(os.environ["SFTP_PORT"])
        self.known_hosts_path = known_hosts_path
        self.project_slug = "test-project"

    def _set_config(self) -> None:
        """Override to avoid Azure Key Vault dependency in tests."""


@pytest.fixture(scope="module")
def host_keys(tmp_path_factory) -> Path:
    """Creates temporary directory for host keys (will be populated by server)"""
    return tmp_path_factory.mktemp("host_keys")


@pytest.fixture(scope="module")
def sftp_server(host_keys) -> Generator[SFTPServer, None, None]:
    """Return a running SFTP server container."""
    server = SFTPServer(host_keys)
    server.start()
    yield server
    server.stop()


@pytest.fixture()
def sftp_uploader(host_keys) -> MockSFTPUploader:
    """Return a MockSFTPUploader object."""
    return MockSFTPUploader(host_keys / "known_hosts")


@pytest.fixture()
def zip_content() -> Generator:
    """Directory containing the test data for uploading to the sftp server."""
    test_zip_file = TEST_DIR / "data" / "public.zip"
    with test_zip_file.open("rb") as file_content:
        yield file_content


def test_send_via_sftp(
    zip_content, not_yet_exported_dicom_image, sftp_uploader, sftp_server
) -> None:
    """Tests that DICOM image can be uploaded to the correct location via SFTP"""
    # ARRANGE
    pseudo_anon_id = not_yet_exported_dicom_image.pseudo_study_uid
    project_slug = "some-project-slug"
    expected_output_file = sftp_server.mounted_upload_dir / project_slug / (pseudo_anon_id + ".zip")

    # The mock SFTP server requires files to be uploaded to the upload/ directory
    remote_directory = f"{SFTP_UPLOAD_DIR}/{project_slug}"

    # ACT
    sftp_uploader.send_via_sftp(zip_content, pseudo_anon_id, remote_directory)

    # ASSERT
    assert expected_output_file.exists()


def test_update_exported_and_save(rows_in_session) -> None:
    """Tests that the exported_at field is updated when a file is uploaded"""
    # ARRANGE
    expected_export_time = datetime.now(tz=UTC)

    # ACT
    update_exported_at(generate_uid(entropy_srcs=["not_yet_exported"]), expected_export_time)
    new_row = (
        rows_in_session.query(Image)
        .filter(Image.pseudo_study_uid == generate_uid(entropy_srcs=["not_yet_exported"]))
        .one()
    )
    actual_export_time = new_row.exported_at.replace(tzinfo=UTC)

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
        extract_datetime=datetime.now(tz=UTC),
        export_dir=export_dir,
    )


def test_upload_parquet(parquet_export, sftp_uploader, sftp_server) -> None:
    """Tests that parquet files are uploaded to the correct location via SFTP"""
    # ARRANGE
    # Set up the mock server directory
    parquet_export.copy_to_exports(Path(__file__).parents[3] / "test" / "resources" / "omop")
    parquet_export.export_radiology_linker(pd.DataFrame(list("dummy"), columns=["D"]))

    # ACT
    sftp_uploader.upload_parquet_files(parquet_export, SFTP_UPLOAD_DIR)

    # ASSERT
    expected_public_parquet_dir = (
        sftp_server.mounted_upload_dir
        / parquet_export.project_slug
        / parquet_export.extract_time_slug
        / "parquet"
    )
    assert expected_public_parquet_dir.exists()

    # Print difference report to aid debugging (it doesn't actually assert anything)
    dc = filecmp.dircmp(parquet_export.current_extract_base, expected_public_parquet_dir)
    dc.report_full_closure()
    assert (
        expected_public_parquet_dir / "omop" / "public" / "PROCEDURE_OCCURRENCE.parquet"
    ).exists(), "Public PROCEDURE_OCCURRENCE.parquet file not found"
    assert (
        expected_public_parquet_dir / "radiology" / "IMAGE_LINKER.parquet"
    ).exists(), "Radiology IMAGE_LINKER.parquet file not found"


def test_no_export_to_upload(parquet_export, sftp_uploader, sftp_server) -> None:
    """If there is nothing in the export directory, an exception is thrown"""
    # ARRANGE
    parquet_export.public_output.mkdir(parents=True, exist_ok=True)

    # ACT & ASSERT
    with pytest.raises(FileNotFoundError):
        sftp_uploader.upload_parquet_files(parquet_export, SFTP_UPLOAD_DIR)
