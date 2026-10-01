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

import threading
import typing
from contextlib import contextmanager, redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Generator

from loguru import logger

from dicom_validator.spec_reader.edition_reader import EditionReader
from dicom_validator.tag_tools import tag_name_from_id
from dicom_validator.validator.error_handler import (
    NullValidationResultHandler,
    ValidationResultFormatter,
)
from dicom_validator.validator.iod_validator import IODValidator
from dicom_validator.validator.validation_result import (
    DicomTag,
    ModuleErrors,
    Status,
    TagError,
    ValidationResult,
)
from pydicom import Dataset

from core.exceptions import PixlSkipInstanceError

if typing.TYPE_CHECKING:
    from loguru import Logger


class DicomValidator:
    def __init__(self, edition: str = "current"):
        self.edition = edition

        # Default from dicom_validator but defining here to be explicit
        standard_path = str(Path.home() / "dicom-validator")
        with _redirect_stdout_to_debug(logger):
            edition_reader = EditionReader(standard_path)
            self.dicom_info = edition_reader.dicom_info_for_edition(self.edition)

        # Used to format errors introduced by de-identification
        self.formatter = ValidationResultFormatter(self.dicom_info.dictionary)

    def _validate(self, dataset: Dataset) -> ValidationResult:
        """Validate a pydicom Dataset using dicom-validator."""
        return IODValidator(
            dataset,
            self.dicom_info,
            error_handler=NullValidationResultHandler(),
        ).validate()

    def _describe_error(self, tag: DicomTag, error: TagError) -> str:
        tag_name = tag_name_from_id(tag.tag, self.dicom_info.dictionary)
        return f"Tag {tag_name}{self.formatter.error_message(error)}"

    def validate_original(self, dataset: Dataset) -> ModuleErrors | None:
        """Check pre-existing validation errors in a dataset.

        Returns:
            module_errors: pre-existing validation errors, keyed by module
                name then DICOM tag, or None if dicom-validator could not
                validate the dataset at all (e.g. missing or unrecognised
                SOP Class UID).
        """
        result = self._validate(dataset)
        if result.status not in (Status.Passed, Status.Failed):
            logger.warning(
                "Cannot check for pre-existing validation errors. "
                "dicom-validator returned status: {}",
                result.status,
            )
            return None

        return result.module_errors

    def validate_anonymised(self, dataset: Dataset) -> ModuleErrors:
        """Validate an anonymised dataset.

        Args:
            dataset: the anonymised dataset to validate.

        Returns:
            module_errors: all validation errors found in the anonymised
                dataset, keyed by module name then DICOM tag. Use
                get_new_errors to determine which of these were introduced
                by anonymisation.

        Raises:
            PixlSkipInstanceError: If dicom-validator could not validate the
                anonymised dataset at all (e.g. missing SOP Class UID).
        """
        result = self._validate(dataset)
        if result.status not in (Status.Passed, Status.Failed):
            msg = (
                "Cannot validate the anonymised dataset. "
                f"dicom-validator returned status: {result.status}"
            )
            raise PixlSkipInstanceError(msg)
        return result.module_errors

    def get_new_errors(
        self, original_errors: ModuleErrors | None, anon_errors: ModuleErrors
    ) -> dict[str, set[str]]:
        """Compare validation errors before and after anonymisation.

        Args:
            original_errors: module_errors returned by validate_original for
                the dataset before anonymisation, or None if the dataset
                hasn't been validated for pre-existing errors.
            anon_errors: module_errors returned by validate_anonymised for
                the dataset after anonymisation.

        Returns:
            new_errors: human-readable errors introduced by anonymisation,
                keyed by module name. If original_errors is None, all errors
                found after anonymisation are returned, as it's not possible
                to tell which of them pre-existed.
        """
        if original_errors is None:
            logger.warning(
                "Cannot determine whether validation errors were introduced by "
                "anonymisation, as the original dataset was not validated. "
                "Errors found after anonymisation: {}",
                anon_errors,
            )
            original_errors = ModuleErrors()

        diff_errors: dict[str, set[str]] = {}
        for module_name, anon_tag_errors in anon_errors.items():
            if module_name in original_errors:
                # keep tags with new errors or errors that have changed
                original_tag_errors = original_errors[module_name]
                new_tag_errors = {
                    tag: error
                    for tag, error in anon_tag_errors.items()
                    if (tag, error) not in original_tag_errors.items()
                }
            else:
                new_tag_errors = anon_tag_errors

            if new_tag_errors:
                diff_errors[module_name] = {
                    self._describe_error(tag, error)
                    for tag, error in new_tag_errors.items()
                }

        return diff_errors


thread_local = threading.local()


@contextmanager
def _redirect_stdout_to_debug(_logger: Logger) -> Generator[None, None, None]:
    """Within the context manager, redirect all print statements to debug statements."""

    # sys.stdout is shared across all threads so use thread-local storage
    if not hasattr(thread_local, "stdout"):
        thread_local.stdout = StringIO()

    with redirect_stdout(thread_local.stdout):
        yield

    thread_local.stdout.seek(0)
    output = thread_local.stdout.readlines()
    for line in output:
        _logger.trace(line.strip())


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
