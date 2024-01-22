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


from datetime import datetime, timezone

import pytest
from core._database import get_project_slug_from_db, update_exported_at_and_save
from core.database import Image
from core.upload import upload_content, upload_dicom_image


@pytest.mark.usefixtures("_run_containers")
def test_upload_content(data, mounted_data) -> None:
    """Tests that file is present on the endpoint after upload"""
    local_file = data / "public.zip"
    with local_file.open("rb") as handle:
        output_file = upload_content(handle, remote_file="public.zip", remote_dir="new_dir")

    assert (mounted_data / output_file).exists()


@pytest.mark.usefixtures("_run_containers")
def test_upload_dicom_image(data, mounted_data, not_yet_exported_dicom_image) -> None:
    """Tests that DICOM image can be uploaded to the correct location"""
    # ARRANGE
    # Get the pseudo identifier from the test image
    pseudo_anon_id = not_yet_exported_dicom_image.hashed_identifier
    project_slug = get_project_slug_from_db(pseudo_anon_id)
    expected_output_file = mounted_data / project_slug / (pseudo_anon_id + ".zip")

    # ACT
    local_file = data / "public.zip"
    upload_dicom_image(local_file, pseudo_anon_id)

    # ASSERT
    assert expected_output_file.exists()


@pytest.mark.usefixtures("_run_containers")
def test_upload_dicom_image_throws(data, already_exported_dicom_image) -> None:
    """Tests that exception thrown if DICOM image already exported"""
    # ARRANGE
    # Get the pseudo identifier from the test image
    pseudo_anon_id = already_exported_dicom_image.hashed_identifier

    # ACT
    local_file = data / "public.zip"

    # ASSERT
    with pytest.raises(RuntimeError, match="Image already exported"):
        upload_dicom_image(local_file, pseudo_anon_id)


@pytest.mark.usefixtures("_run_containers")
def test_update_exported_and_save(rows_in_session) -> None:
    """Tests that the exported_at field is updated when a file is uploaded"""
    # ARRANGE
    expected_export_time = datetime.now(tz=timezone.utc)

    # ACT
    update_exported_at_and_save("not_yet_exported", expected_export_time)
    new_row = (
        rows_in_session.query(Image).filter(Image.hashed_identifier == "not_yet_exported").one()
    )
    actual_export_time = new_row.exported_at.replace(tzinfo=timezone.utc)

    # ASSERT
    assert actual_export_time == expected_export_time
