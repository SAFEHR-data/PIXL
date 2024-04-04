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
from pathlib import Path

import nibabel
import numpy as np
import pydicom
import pytest
import sqlalchemy
from core.db.models import Image
from core.dicom_tags import (
    DICOM_TAG_PROJECT_NAME,
    PrivateDicomTag,
    add_private_tag,
    create_private_tag,
)
from core.project_config import load_project_config, load_tag_operations
from decouple import config
from pixl_dcmd.main import (
    anonymise_dicom,
    apply_tag_scheme,
    remove_overlays,
)
from pydicom.data import get_testdata_file
from pydicom.dataset import Dataset
from pytest_pixl.dicom import generate_dicom_dataset
from pytest_pixl.helpers import run_subprocess

PROJECT_CONFIGS_DIR = Path(config("PROJECT_CONFIGS_DIR"))
TEST_PROJECT_SLUG = "test-extract-uclh-omop-cdm"


@pytest.fixture(scope="module")
def tag_scheme() -> list[dict]:
    """Base tag scheme for testing."""
    tag_ops = load_tag_operations(load_project_config(TEST_PROJECT_SLUG))
    return tag_ops.base[0]


def _mri_diffusion_tags(manufacturer: str = "Philips") -> list[PrivateDicomTag]:
    """
    Private DICOM tags for testing the anonymisation process.
    These tags from `/projects/configs/tag-operations/mri-diffusion.yaml` so we can test
    whether the manufacturer overrides work during anonymisation
    """
    project_config = load_project_config(TEST_PROJECT_SLUG)
    tag_ops = load_tag_operations(project_config)
    manufacturer_overrides = [
        override
        for override in tag_ops.manufacturer_overrides
        if override["manufacturer"] == manufacturer
    ][0]

    return [
        create_private_tag(tag["group"], tag["element"], vr="SH", value="test")
        for tag in manufacturer_overrides["tags"]
    ]


@pytest.fixture()
def vanilla_dicom_image() -> Dataset:
    """
    A DICOM image with diffusion data to test the anonymisation process.
    Private tags were added to match the tag operations defined in the project config, so we can
    test whether the anonymisation process works as expected when defining overrides.
    """
    ds = generate_dicom_dataset(Modality="DX")

    # Make sure the project name tag is added for anonymisation to work
    add_private_tag(ds, DICOM_TAG_PROJECT_NAME)
    # Update the project name tag to a known value
    block = ds.private_block(
        DICOM_TAG_PROJECT_NAME.group_id, DICOM_TAG_PROJECT_NAME.creator_string
    )
    ds[block.get_tag(DICOM_TAG_PROJECT_NAME.offset_id)].value = TEST_PROJECT_SLUG

    return ds


@pytest.fixture()
def mri_diffusion_dicom_image() -> Dataset:
    """
    A DICOM image with diffusion data to test the anonymisation process.
    Private tags were added to match the tag operations defined in the project config, so we can
    test whether the anonymisation process works as expected when defining overrides.
    """
    manufacturer = "Philips"
    ds = generate_dicom_dataset(Manufacturer=manufacturer, Modality="DX")
    tags = _mri_diffusion_tags(manufacturer)
    for tag in tags:
        add_private_tag(ds, tag)

    # Make sure the project name tag is added for anonymisation to work
    add_private_tag(ds, DICOM_TAG_PROJECT_NAME)
    # Update the project name tag to a known value
    block = ds.private_block(
        DICOM_TAG_PROJECT_NAME.group_id, DICOM_TAG_PROJECT_NAME.creator_string
    )
    ds[block.get_tag(DICOM_TAG_PROJECT_NAME.offset_id)].value = TEST_PROJECT_SLUG

    return ds


def test_remove_overlay_plane() -> None:
    """Checks that overlay planes are removed."""
    ds = get_testdata_file(
        "MR-SIEMENS-DICOM-WithOverlays.dcm", read=True, download=True
    )
    assert (0x6000, 0x3000) in ds

    ds_minus_overlays = remove_overlays(ds)
    assert (0x6000, 0x3000) not in ds_minus_overlays


def test_anonymisation(row_for_dicom_testing, vanilla_dicom_image: Dataset) -> None:
    """
    Test whether anonymisation works as expected on a vanilla DICOM dataset
    """

    orig_patient_id = vanilla_dicom_image.PatientID
    orig_patient_name = vanilla_dicom_image.PatientName

    # Sanity check: study date should be present before anonymisation
    assert vanilla_dicom_image.StudyDate is not None

    anon_ds = anonymise_dicom(vanilla_dicom_image)

    assert anon_ds.PatientID != orig_patient_id
    assert anon_ds.PatientName != orig_patient_name
    assert "StudyDate" not in anon_ds


def test_anonymisation_with_overrides(
    row_for_dicom_testing, mri_diffusion_dicom_image: Dataset
) -> None:
    """
    Test that the anonymisation process works with manufacturer overrides.
    GIVEN a dicom image with manufacturer-specific private tags
    WHEN the anonymisation is applied
    THEN all tag operations should be applied, obeying any manufacturer overrides
    """

    # Sanity check
    # (0x2001, 0x1003) is one of the tags whitelisted by the overrides for Philips manufacturer
    assert (0x2001, 0x1003) in mri_diffusion_dicom_image
    original_patient_id = mri_diffusion_dicom_image.PatientID
    original_private_tag = mri_diffusion_dicom_image[(0x2001, 0x1003)]

    anon_ds = anonymise_dicom(mri_diffusion_dicom_image)

    # Whitelisted tags should still be present
    assert (0x0010, 0x0020) in anon_ds
    assert (0x2001, 0x1003) in anon_ds
    assert anon_ds.PatientID != original_patient_id
    assert mri_diffusion_dicom_image[(0x2001, 0x1003)] == original_private_tag


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
