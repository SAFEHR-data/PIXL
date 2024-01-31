#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
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
from __future__ import annotations

import pathlib

import pydicom
import pytest
import sqlalchemy
import yaml
from pydicom.data import get_testdata_file

from core.db.models import Image
from pixl_dcmd.main import (
    apply_tag_scheme,
    remove_overlays,
)


@pytest.fixture(scope="module")
def tag_scheme() -> dict:
    """Read the tag scheme from orthanc raw."""
    tag_file = (
        pathlib.Path(__file__).parents[2]
        / "orthanc/orthanc-anon/plugin/tag-operations.yaml"
    )
    return yaml.safe_load(tag_file.read_text())


def test_remove_overlay_plane() -> None:
    """Checks that overlay planes are removed."""
    ds = get_testdata_file(
        "MR-SIEMENS-DICOM-WithOverlays.dcm", read=True, download=True
    )
    assert (0x6000, 0x3000) in ds

    ds_minus_overlays = remove_overlays(ds)
    assert (0x6000, 0x3000) not in ds_minus_overlays


# TODO: Produce more complete test coverage for anonymisation
# https://github.com/UCLH-Foundry/PIXL/issues/132
def test_image_already_exported_throws(rows_in_session, tag_scheme):
    """
    GIVEN a dicom image which has no un-exported rows in the pipeline database
    WHEN the dicom tag scheme is applied
    THEN an exception will be thrown as
    """
    exported_dicom = pathlib.Path(__file__).parents[2] / "test/resources/Dicom1.dcm"
    input_dataset = pydicom.dcmread(exported_dicom)

    with pytest.raises(sqlalchemy.exc.NoResultFound):
        apply_tag_scheme(input_dataset, tag_scheme)


def test_pseudo_identifier_processing(rows_in_session, tag_scheme):
    """
    GIVEN a dicom image that hasn't been exported in the pipeline db
    WHEN the dicom tag scheme is applied
    THEN the patient identifier tag should be the mrn and accession hashed
      and the pipeline db row should now have the fake hash
    """
    exported_dicom = pathlib.Path(__file__).parents[2] / "test/resources/Dicom2.dcm"
    input_dataset = pydicom.dcmread(exported_dicom)

    accession_number = "AA12345605"
    mrn = "987654321"
    fake_hash = "-".join(list(f"{mrn}{accession_number}"))
    print("fake_hash = ", fake_hash)
    output_dataset = apply_tag_scheme(input_dataset, tag_scheme)
    image = (
        rows_in_session.query(Image)
        .filter(Image.accession_number == "AA12345605")
        .one()
    )
    print("after tags applied")
    assert output_dataset[0x0010, 0x0020].value == fake_hash
    assert image.hashed_identifier == fake_hash
