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

"""Tests for the TRE API uploader module."""

from __future__ import annotations

import filecmp
import zipfile
from collections.abc import Generator
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
import requests
from pydicom.uid import generate_uid

from core.db.models import Image
from core.db.queries import update_exported_at
from core.uploader._treapi import TreApiUploader, _create_zip_archive

# Constants
TEST_DIR = Path(__file__).parents[1]
MOCK_API_TOKEN = "test_token_123"
MOCK_HOST = "https://api.example.com"

# HTTP Status Codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_UNAUTHORIZED = 401
HTTP_BAD_REQUEST = 400


class MockTreApiUploader(TreApiUploader):
    """Mock TRE API uploader for testing without real API calls."""

    def __init__(self) -> None:
        """Initialize mock uploader with test configuration."""
        self.host = MOCK_HOST
        self.token = MOCK_API_TOKEN
        self.headers = {"Authorization": f"Bearer {self.token}"}


@pytest.fixture
def mock_uploader(mocker) -> MockTreApiUploader:
    """Create a mock TRE API uploader with HTTP requests mocked."""
    # Mock all HTTP requests
    mock_get = mocker.patch("core.uploader._treapi.requests.get")
    mock_post = mocker.patch("core.uploader._treapi.requests.post")
    mock_put = mocker.patch("core.uploader._treapi.requests.put")

    # Configure default successful responses
    _configure_success_responses(mock_get, mock_post, mock_put, mocker)

    return MockTreApiUploader()


def _configure_success_responses(mock_get, mock_post, mock_put, mocker) -> None:
    """Configure mock responses for successful API calls."""
    # Token validation response
    token_response = mocker.Mock()
    token_response.raise_for_status.return_value = None
    token_response.status_code = HTTP_OK
    mock_get.return_value = token_response

    # Upload response
    upload_response = mocker.Mock()
    upload_response.raise_for_status.return_value = None
    upload_response.status_code = HTTP_CREATED
    mock_post.return_value = upload_response

    # Flush response
    flush_response = mocker.Mock()
    flush_response.raise_for_status.return_value = None
    flush_response.status_code = HTTP_CREATED
    mock_put.return_value = flush_response


@pytest.fixture
def test_zip_content() -> Generator[BytesIO, None, None]:
    """Provide test zip file content."""
    test_zip_path = TEST_DIR / "data" / "public.zip"
    with test_zip_path.open("rb") as file_content:
        yield BytesIO(file_content.read())


@pytest.fixture
def parquet_export(export_dir):
    """
    Create a ParquetExport instance for testing.

    Note: Import is done locally to avoid circular dependencies.
    """
    from core.exports import ParquetExport

    return ParquetExport(
        project_name_raw="test-project",
        extract_datetime=datetime.now(tz=UTC),
        export_dir=export_dir,
    )


class TestTreApiUploader:
    """Test suite for TRE API uploader functionality."""

    def test_send_via_api_success(
        self, test_zip_content, not_yet_exported_dicom_image, mock_uploader, mocker
    ) -> None:
        """Test successful data upload via API."""
        # Arrange
        pseudo_id = not_yet_exported_dicom_image.pseudo_study_uid
        filename = f"{pseudo_id}.zip"

        mock_is_token_valid = mocker.patch.object(
            mock_uploader, "_is_token_valid", return_value=True
        )
        mock_upload_file = mocker.patch.object(mock_uploader, "_upload_file")

        # Act
        mock_uploader.send_via_api(test_zip_content, filename)

        # Assert
        mock_is_token_valid.assert_called_once()
        mock_upload_file.assert_called_once_with(test_zip_content, filename)

    def test_send_via_api_invalid_token(self, test_zip_content, mock_uploader, mocker) -> None:
        """Test API upload with invalid token raises error."""
        # Arrange
        mock_is_token_valid = mocker.patch.object(
            mock_uploader, "_is_token_valid", return_value=False
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Token invalid"):
            mock_uploader.send_via_api(test_zip_content, "test.zip")

        mock_is_token_valid.assert_called_once()

    def test_upload_dicom_image(self, not_yet_exported_dicom_image, mock_uploader, mocker) -> None:
        """Test DICOM image upload workflow."""
        # Arrange
        study_id = "test_study_123"
        study_tags = Mock()
        study_tags.pseudo_anon_image_id = not_yet_exported_dicom_image.pseudo_study_uid

        mock_zip_content = BytesIO(b"mock_zip_data")
        mock_get_study_zip = mocker.patch(
            "core.uploader._treapi.get_study_zip_archive", return_value=mock_zip_content
        )
        mock_send_via_api = mocker.patch.object(mock_uploader, "send_via_api")
        mock_flush = mocker.patch.object(mock_uploader, "flush")

        # Act
        mock_uploader._upload_dicom_image(study_id, study_tags)

        # Assert
        mock_get_study_zip.assert_called_once_with(study_id)
        mock_send_via_api.assert_called_once_with(mock_zip_content, study_tags.pseudo_anon_image_id)
        mock_flush.assert_called_once()

    def test_token_validation_success(self, mock_uploader, mocker) -> None:
        """Test successful token validation."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = HTTP_OK
        mock_response.raise_for_status.return_value = None
        mock_get = mocker.patch("core.uploader._treapi.requests.get", return_value=mock_response)

        # Act
        result = mock_uploader._is_token_valid()

        # Assert
        assert result is True
        mock_get.assert_called_once_with(
            url=f"{mock_uploader.host}/tokens/info",
            headers=mock_uploader.headers,
            timeout=10,
        )

    def test_token_validation_failure(self, mock_uploader, mocker) -> None:
        """Test token validation failure."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = HTTP_UNAUTHORIZED
        mock_response.raise_for_status.return_value = None
        mocker.patch("core.uploader._treapi.requests.get", return_value=mock_response)

        # Act
        result = mock_uploader._is_token_valid()

        # Assert
        assert result is False

    def test_token_validation_request_exception(self, mock_uploader, mocker) -> None:
        """Test token validation with request exception."""
        # Arrange
        mocker.patch(
            "core.uploader._treapi.requests.get",
            side_effect=requests.RequestException("Network error"),
        )

        # Act
        result = mock_uploader._is_token_valid()

        # Assert
        assert result is False

    def test_upload_parquet_files(self, parquet_export, mock_uploader, mocker) -> None:
        """Test parquet files upload as zip archive."""
        # Arrange
        parquet_export.copy_to_exports(Path(__file__).parents[3] / "test" / "resources" / "omop")
        parquet_export.export_radiology_linker(pd.DataFrame(["test_data"], columns=["data"]))

        mock_send_via_api = mocker.patch.object(mock_uploader, "send_via_api")
        mock_flush = mocker.patch.object(mock_uploader, "flush")

        # Act
        mock_uploader.upload_parquet_files(parquet_export)

        # Assert
        mock_send_via_api.assert_called_once()
        mock_flush.assert_called_once()

        # Verify call arguments
        call_args = mock_send_via_api.call_args
        assert isinstance(call_args[0][0], BytesIO)
        assert call_args[0][1] == f"{parquet_export.current_extract_base.name}.zip"

    def test_upload_parquet_files_no_files(self, parquet_export, mock_uploader) -> None:
        """Test error when no parquet files are found."""
        # Arrange
        parquet_export.public_output.mkdir(parents=True, exist_ok=True)

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="No parquet files found"):
            mock_uploader.upload_parquet_files(parquet_export)


class TestDatabaseOperations:
    """Test suite for database-related operations."""

    def test_update_exported_timestamp(self, rows_in_session) -> None:
        """Test updating the exported timestamp in the database."""
        # Arrange
        expected_export_time = datetime.now(tz=UTC)
        uid = generate_uid(entropy_srcs=["not_yet_exported"])

        # Act
        update_exported_at(uid, expected_export_time)

        # Retrieve updated record
        updated_record = rows_in_session.query(Image).filter(Image.pseudo_study_uid == uid).one()
        actual_export_time = updated_record.exported_at.replace(tzinfo=UTC)

        # Assert
        assert actual_export_time == expected_export_time


class TestUtilityFunctions:
    """Test suite for utility functions."""

    def test_create_zip_archive_preserves_dir_structure(self, tmp_path) -> None:
        """Test zip archive creation with directory structure."""
        # Arrange
        test_files = self._create_test_files(tmp_path)
        zip_filename = str(tmp_path / "dir_structure.zip")

        # Act
        zip_path = _create_zip_archive(test_files, self.root_dir, zip_filename)

        # Assert
        assert zip_path.exists()
        assert zipfile.is_zipfile(str(zip_path))

        # Extract archive and verify contents
        extract_path = tmp_path / "extracted"
        with zipfile.ZipFile(str(zip_path), "r") as zipf:
            zipf.extractall(extract_path)

        # Print difference report to aid debugging (it doesn't actually assert anything)
        dc = filecmp.dircmp(tmp_path / self.root_dir, extract_path)
        dc.report_full_closure()

        assert extract_path.exists()
        assert (extract_path / "dir1" / "file1.txt").exists()
        assert (extract_path / "dir2" / "subdir" / "file2.txt").exists()

    def test_create_zip_archive_empty_files(self, tmp_path) -> None:
        """Test zip archive creation with empty file list."""
        # Arrange
        zip_filename = str(tmp_path / "empty.zip")

        # Act
        zip_path = _create_zip_archive([], zip_filename)

        # Assert
        assert zip_path.exists()
        assert zipfile.is_zipfile(str(zip_path))

        # Verify empty zip
        with zipfile.ZipFile(str(zip_path), "r") as zipf:
            assert len(zipf.namelist()) == 0

    def _create_test_files(self, tmp_path: Path) -> list[Path]:
        """Create test files with directory structure for zip archive testing."""
        self.root_dir = tmp_path / "root"
        dir1 = self.root_dir / "dir1"
        dir2 = self.root_dir / "dir2" / "subdir"
        file1 = dir1 / "file1.txt"
        file2 = dir2 / "file2.txt"

        self.root_dir.mkdir(parents=True)
        dir1.mkdir(parents=True)
        dir2.mkdir(parents=True)
        file1.write_text("Content of file 1")
        file2.write_text("Content of file 2")

        return [file1, file2]
