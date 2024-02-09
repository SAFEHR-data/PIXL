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
"""Test functionality to upload files to an endpoint."""


import pathlib
from datetime import datetime, timezone

import pytest
from core.db.models import Image
from core.db.queries import get_project_slug_from_db, update_exported_at
from core.upload import upload_dicom_image, upload_parquet_files


@pytest.mark.usefixtures("ftps_server")
def test_upload_dicom_image(test_zip_content, not_yet_exported_dicom_image, ftps_home_dir) -> None:
    """Tests that DICOM image can be uploaded to the correct location"""
    # ARRANGE
    # Get the pseudo identifier from the test image
    pseudo_anon_id = not_yet_exported_dicom_image.hashed_identifier
    project_slug = get_project_slug_from_db(pseudo_anon_id)
    expected_output_file = ftps_home_dir / project_slug / (pseudo_anon_id + ".zip")

    # ACT
    upload_dicom_image(test_zip_content, pseudo_anon_id)

    # ASSERT
    assert expected_output_file.exists()


@pytest.mark.usefixtures("ftps_server")
def test_upload_dicom_image_throws(test_zip_content, already_exported_dicom_image) -> None:
    """Tests that exception thrown if DICOM image already exported"""
    # ARRANGE
    # Get the pseudo identifier from the test image
    pseudo_anon_id = already_exported_dicom_image.hashed_identifier

    # ASSERT
    with pytest.raises(RuntimeError, match="Image already exported"):
        upload_dicom_image(test_zip_content, pseudo_anon_id)


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


@pytest.mark.usefixtures("ftps_server")
def test_upload_parquet(parquet_export, ftps_home_dir) -> None:
    """Tests that parquet files are uploaded to the correct location"""
    # ARRANGE

    parquet_export.copy_to_exports(
        pathlib.Path(__file__).parents[2] / "test" / "resources" / "omop"
    )
    with (parquet_export.public_output.parent / "radiology.parquet").open("w") as handle:
        handle.writelines(["dummy data"])

    # ACT
    upload_parquet_files(parquet_export)
    # ASSERT
    expected_public_parquet_dir = (
        ftps_home_dir / parquet_export.project_slug / parquet_export.extract_time_slug / "parquet"
    )
    assert expected_public_parquet_dir.exists()
    assert (expected_public_parquet_dir / "PROCEDURE_OCCURRENCE.parquet").exists()
    assert (expected_public_parquet_dir / "radiology.parquet").exists()


@pytest.mark.usefixtures("ftps_server")
def test_no_export_to_upload(parquet_export) -> None:
    """If there is nothing in the export directly, an exception is thrown"""
    parquet_export.public_output.mkdir(parents=True, exist_ok=True)
    with pytest.raises(FileNotFoundError):
        upload_parquet_files(parquet_export)
