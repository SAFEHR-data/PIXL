"""Test functionality to upload files to an endpoint."""


import pytest
from core.upload import upload_as_file


@pytest.mark.usefixtures("_run_containers")
def test_upload_file(data, mounted_data) -> None:
    """Tests that file is present on the endpoint after upload"""
    local_file = data / "public.zip"
    with local_file.open("rb") as handle:
        output_file = upload_as_file(handle, "public.zip")

    assert (mounted_data / output_file).exists()
