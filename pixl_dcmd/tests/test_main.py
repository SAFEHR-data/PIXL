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

import nibabel
import numpy as np
import pydicom
import pytest
import sqlalchemy
import yaml
from core.db.models import Image
from core.project_config import TagOperations
from pixl_dcmd.main import (
    _load_scheme,
    apply_tag_scheme,
    merge_tag_schemes,
    remove_overlays,
)
from pydicom.data import get_testdata_file
from pytest_pixl.helpers import run_subprocess

BASE_TAGS_FILE = (
    pathlib.Path(__file__).parents[2]
    / "projects/configs/tag-operations/test-extract-uclh-omop-cdm.yaml"
)


@pytest.fixture(scope="module")
def tag_scheme() -> list[dict]:
    """Read the tag scheme from orthanc raw."""
    return _load_scheme(BASE_TAGS_FILE)


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


def test_can_nifti_convert_post_anonymisation(
    row_for_dicom_testing, tmp_path, directory_of_mri_dicoms, tag_scheme
):
    """Can a DICOM image that has passed through our tag processing be converted to NIFTI"""
    # Create a directory to store anonymised DICOM files
    anon_dicom_dir = tmp_path / "anon"
    anon_dicom_dir.mkdir()

    # Get test DICOMs from the fixture, anonymise and save
    for dcm_path in directory_of_mri_dicoms.glob("*.dcm"):
        dcm_identifiable = pydicom.dcmread(dcm_path)
        dcm_anon = apply_tag_scheme(dcm_identifiable, tag_scheme)
        pydicom.dcmwrite(anon_dicom_dir / dcm_path.name, dcm_anon)

    # Convert the anonymised DICOMs to NIFTI with dcm2niix
    anon_nifti_dir = tmp_path / "nifti_anon"
    anon_nifti_dir.mkdir()
    run_subprocess(
        ["dcm2niix", "-f", "anon", "-o", str(anon_nifti_dir), str(anon_dicom_dir)],
    )

    # Convert the pre-anonymisation DICOMs to NIFTI with dcm2niix
    ident_nifti_dir = tmp_path / "nifti_ident"
    ident_nifti_dir.mkdir()
    run_subprocess(
        [
            "dcm2niix",
            "-f",
            "ident",
            "-o",
            str(ident_nifti_dir),
            str(directory_of_mri_dicoms),
        ],
    )

    # Confirm that the shape, orientation and contents of the pre- and
    # post- anonymisation images match
    anon_nifti = nibabel.load(anon_nifti_dir / "anon.nii")
    ident_nifti = nibabel.load(ident_nifti_dir / "ident.nii")
    assert anon_nifti.shape == ident_nifti.shape
    assert np.all(anon_nifti.header.get_sform() == ident_nifti.header.get_sform())
    assert np.all(anon_nifti.get_fdata() == ident_nifti.get_fdata())


BASE_ONLY_TAG_OPS = TagOperations(base="base.yaml", manufacturer_overrides=None)


@pytest.fixture()
def base_only_tag_scheme() -> TagOperations:
    return TagOperations(base=str(BASE_TAGS_FILE), manufacturer_overrides=None)


def test_merge_base_only_tags(base_only_tag_scheme):
    """
    GIVEN TagOperations with only a base file
    WHEN the tag schemes are merged
    THEN the result should be the same as the base file
    """
    tags = merge_tag_schemes(base_only_tag_scheme)
    expected = _load_scheme(BASE_TAGS_FILE)
    assert tags == expected


@pytest.fixture(scope="module")
def tag_ops_with_manufacturer_overrides(tmp_path_factory):
    """
    TagOperations with a base file and manufacturer overrides, where the base file has 3 tags
    and the manufacturer overrides ovverrides 1 of them and has 2 extra tags.
    This is intetnionally not added in conftest.py because the `PROJECT_CONFIG_DIR` envvar nees to
    be set before importing core.project_config.TagOperations.
    """
    base_tags = [
        {"name": "tag1", "group": 0x001, "element": 0x1000, "op": "delete"},
        {"name": "tag2", "group": 0x002, "element": 0x1001, "op": "delete"},
        {"name": "tag3", "group": 0x003, "element": 0x1002, "op": "delete"},
    ]
    manufacturer_overrides_tags = [
        {
            "manufacturer": "manufacturer_1",
            "tags": [
                # Override tag1 for manufacturer 1
                {"name": "tag1", "group": 0x001, "element": 0x1000, "op": "keep"},
                {"name": "tag4", "group": 0x004, "element": 0x1011, "op": "delete"},
                {"name": "tag5", "group": 0x005, "element": 0x1012, "op": "delete"},
            ],
        },
        {
            "manufacturer": "manufacturer_2",
            "tags": [
                {"name": "tag6", "group": 0x006, "element": 0x1100, "op": "keep"},
                {"name": "tag7", "group": 0x007, "element": 0x1111, "op": "delete"},
                # Override tag3 for manufacturer 2
                {"name": "tag3", "group": 0x003, "element": 0x1002, "op": "keep"},
            ],
        },
    ]

    tmpdir = tmp_path_factory.mktemp("tag-operations")
    base_tags_path = tmpdir / "base.yaml"
    with open(base_tags_path, "w") as f:
        f.write(yaml.dump(base_tags))
    manufacturer_overrides_path = tmpdir / "manufacturer_overrides.yaml"
    with open(manufacturer_overrides_path, "w") as f:
        f.write(yaml.dump(manufacturer_overrides_tags))

    return TagOperations(
        base=str(base_tags_path),
        manufacturer_overrides=str(manufacturer_overrides_path),
    )


def test_manufacturer_overrides_tag_scheme(tag_ops_with_manufacturer_overrides):
    """
    GIVEN TagOperations with a base file and manufacturer overrides, where the base file has 3 tags
        and the manufacturer overrides ovverrides 1 of them and has 2 extra tags
    WHEN the tag schemes are merged
    THEN the result should be the base file with the manufacturer overrides applied
    """
    tags = merge_tag_schemes(
        tag_ops_with_manufacturer_overrides, manufacturer="manufacturer_1"
    )

    # Check that we have the tags
    assert len(tags) == 5
    assert [tag["name"] for tag in tags] == ["tag1", "tag2", "tag3", "tag4", "tag5"]

    # Check that the overridden tag has the correct value
    overridden_tag = next(tag for tag in tags if tag["name"] == "tag1")
    assert overridden_tag["op"] == "keep"
