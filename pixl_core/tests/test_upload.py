"""Test functionality to upload files to an endpoint."""


import pytest
from core.upload import upload_content


@pytest.mark.usefixtures("_run_containers")
def test_upload_content(data, mounted_data) -> None:
    """Tests that file is present on the endpoint after upload"""
    local_file = data / "public.zip"
    with local_file.open("rb") as handle:
        output_file = upload_content(handle, remote_file="public.zip", remote_dir="new_dir")

    assert (mounted_data / output_file).exists()
