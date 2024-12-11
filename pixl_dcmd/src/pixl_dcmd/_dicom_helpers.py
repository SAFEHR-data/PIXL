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
"""Helper functions for DICOM data."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from dicom_validator.spec_reader.edition_reader import EditionReader
from dicom_validator.validator.iod_validator import IODValidator
from pydicom import Dataset


class DicomValidator:
    def __init__(self, edition: str = "current"):
        self.edition = edition

        # Default from dicom_validator but defining here to be explicit
        standard_path = str(Path.home() / "dicom-validator")
        edition_reader = EditionReader(standard_path)
        destination = edition_reader.get_revision(self.edition, False)
        json_path = Path(destination, "json")
        self.dicom_info = EditionReader.load_dicom_info(json_path)

    def validate_original(self, dataset: Dataset) -> None:
        self.original_errors = IODValidator(
            dataset,
            self.dicom_info,
            log_level=logging.ERROR,
        ).validate()

    def validate_anonymised(self, dataset: Dataset) -> dict:
        # Check that the original dataset has been validated
        try:
            orig_errors = self.original_errors
        except AttributeError:
            raise ValueError("Original dataset not yet validated")

        self.anon_errors = IODValidator(
            dataset,
            self.dicom_info,
            log_level=logging.ERROR,
        ).validate()
        self.diff_errors: dict = {}

        for key in self.anon_errors.keys():
            if key in self.original_errors.keys():
                # Keep only errors introduced after the anonymisation
                # The keys of the dictionary containt the actual errors
                diff = set(self.anon_errors[key].keys()) - set(orig_errors[key].keys())
                if diff:
                    self.diff_errors[key] = diff
            else:
                self.diff_errors[key] = self.anon_errors[key]

        return self.diff_errors


@dataclass
class StudyInfo:
    """Identifiers used for an imaging study"""

    mrn: str
    accession_number: str
    study_uid: str


def get_study_info(dataset: Dataset) -> StudyInfo:
    """Read study identifiers from dicom dataset."""
    return StudyInfo(
        mrn=dataset[0x0010, 0x0020].value,
        accession_number=dataset[0x0008, 0x0050].value,
        study_uid=dataset[0x0020, 0x000D].value,
    )
