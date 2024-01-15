"""Test functionality to upload files to an endpoint."""


import pytest
from core.upload import upload_file


@pytest.mark.usefixtures("_run_containers")
def test_upload_file(data, mounted_data) -> None:
    """Tests that file is present on the endpoint after upload"""
    local_file = data / "public.zip"
    output_file = upload_file(local_file)

    assert (mounted_data / output_file).exists()
