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

import pytest
from core.exceptions import PixlSkipInstanceError
from dicom_validator.validator.validation_result import ErrorCode
from pixl_dcmd.dicom_helpers import DicomValidator
from pixl_dcmd.main import anonymise_dicom
from pydicom import Dataset
from pydicom.dataelem import DataElement


def test_validation_check_works(vanilla_dicom_image_DX: Dataset) -> None:
    """
    GIVEN a DICOM dataset
    WHEN the dataset is validated against itself (withouth anonymisation)
    THEN no errors should be raised
    """
    validator = DicomValidator()
    original_errors = validator.validate_original(vanilla_dicom_image_DX)
    assert not validator.validate_anonymised(vanilla_dicom_image_DX, original_errors)


def test_validation_after_anonymisation_works(
    vanilla_dicom_image_DX: Dataset,
    test_project_config,
) -> None:
    """
    GIVEN a DICOM dataset
    WHEN the dataset is validated after anonymisation
    THEN no errors should be raised
    """
    validator = DicomValidator()
    original_errors = validator.validate_original(vanilla_dicom_image_DX)
    anonymise_dicom(vanilla_dicom_image_DX, config=test_project_config)

    assert not validator.validate_anonymised(vanilla_dicom_image_DX, original_errors)


@pytest.fixture()
def non_compliant_dicom_image(vanilla_dicom_image_DX: Dataset) -> Dataset:
    """A DICOM dataset that is not compliant with the DICOM standard."""
    del vanilla_dicom_image_DX.PatientName
    return vanilla_dicom_image_DX


def test_validation_passes_for_non_compliant_dicom(non_compliant_dicom_image) -> None:
    """
    GIVEN a DICOM dataset that is not compliant with the DICOM standard
    WHEN the dataset is validated after anonymisation
    THEN no errors should be raised
    """
    validator = DicomValidator()
    original_errors = validator.validate_original(non_compliant_dicom_image)
    assert not validator.validate_anonymised(non_compliant_dicom_image, original_errors)


def test_validation_fails_after_invalid_tag_modification(
    vanilla_dicom_image_DX,
) -> None:
    """
    GIVEN a DICOM dataset
    WHEN an invalid tag operation is performed (e.g. deleting a required tag)
    THEN validation should return a non-empty list of errors
    """
    validator = DicomValidator()
    original_errors = validator.validate_original(vanilla_dicom_image_DX)
    del vanilla_dicom_image_DX.PatientName
    validation_result = validator.validate_anonymised(
        vanilla_dicom_image_DX, original_errors
    )

    assert len(validation_result) == 1
    assert "Patient" in validation_result.keys()
    assert len(validation_result["Patient"]) == 1
    assert "Tag (0010,0010) (Patient's Name) is missing" in validation_result["Patient"]


@pytest.fixture()
def dicom_with_malformed_sequence_tag(vanilla_dicom_image_DX: Dataset) -> Dataset:
    """
    A DICOM dataset with a non-conformant Derivation Code Sequence tag: it should
    have VR SQ, but instead has VR OB.
    """
    vanilla_dicom_image_DX.add(
        DataElement("DerivationCodeSequence", "OB", b"\x00" * 10)
    )
    return vanilla_dicom_image_DX


def test_validate_original_reports_malformed_sequence(
    dicom_with_malformed_sequence_tag: Dataset,
) -> None:
    """
    GIVEN a DICOM dataset with a malformed sequence tag
    WHEN the original dataset is validated
    THEN an InvalidSequence error is returned
    """
    validator = DicomValidator()
    original_errors = validator.validate_original(dicom_with_malformed_sequence_tag)

    error_codes = {
        error.code
        for tag_errors in original_errors.values()
        for error in tag_errors.values()
    }
    assert ErrorCode.InvalidSequence in error_codes


def test_validate_anonymised_returns_all_errors_when_original_unknown(
    vanilla_dicom_image_DX: Dataset,
) -> None:
    """
    GIVEN an anonymised dataset that has not been validated for pre-existing errors
    WHEN the anonymised dataset is validated
    THEN all errors found are returned
    """
    validator = DicomValidator()
    del vanilla_dicom_image_DX.PatientName

    validation_result = validator.validate_anonymised(vanilla_dicom_image_DX, None)
    assert "Patient" in validation_result.keys()


@pytest.fixture()
def dicom_missing_sop_class_uid(vanilla_dicom_image_DX: Dataset) -> Dataset:
    """A DICOM dataset with no SOP Class UID, which dicom-validator cannot validate."""
    del vanilla_dicom_image_DX.SOPClassUID
    return vanilla_dicom_image_DX


def test_validate_original_returns_none_when_dataset_cannot_be_validated(
    dicom_missing_sop_class_uid: Dataset,
) -> None:
    """
    GIVEN a DICOM dataset that dicom-validator cannot validate at all
    WHEN the original dataset is validated
    THEN None is returned
    """
    validator = DicomValidator()
    original_errors = validator.validate_original(dicom_missing_sop_class_uid)
    assert original_errors is None


def test_validate_anonymised_raises_skip_instance_error_when_dataset_cannot_be_validated(
    dicom_missing_sop_class_uid: Dataset,
) -> None:
    """
    GIVEN an anonymised DICOM dataset that dicom-validator cannot validate at all
    WHEN the anonymised dataset is validated
    THEN a PixlSkipInstanceError is raised
    """
    validator = DicomValidator()

    with pytest.raises(PixlSkipInstanceError):
        validator.validate_anonymised(dicom_missing_sop_class_uid, None)
