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
import logging
from io import StringIO
from pathlib import Path
from typing import Generator

from loguru import logger

from dicom_validator.spec_reader.edition_reader import EditionReader
from dicom_validator.validator.iod_validator import IODValidator
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
            destination = edition_reader.get_revision(self.edition, False)
        json_path = Path(destination, "json")
        self.dicom_info = EditionReader.load_dicom_info(json_path)

    def validate_original(self, dataset: Dataset) -> dict | None:
        """Check pre-existing validation errors in a dataset.

        Returns:
            validation_errors: a dictionary of validation errors, or None
                if dicom-validator raised a RuntimeError during validation.
        """
        validator = IODValidator(
            dataset,
            self.dicom_info,
            log_level=logging.ERROR,
        )
        try:
            errors: dict | None = validator.validate()
        except RuntimeError as error:
            logger.warning(
                "Cannot check for pre-existing validation errors. "
                "dicom-validator raised a RuntimeError during validation: {}",
                error,
            )
            errors = None

        return errors

    def validate_anonymised(
        self, dataset: Dataset, original_errors: dict | None
    ) -> dict:
        """Check validation errors introduced during de-identification.

        Args:
            original_errors: dict of errors returned by validate_original for
                dataset before anonymisation, or None if the dataset hasn't
                been validated for pre-existing errors.

        Returns:
            new_errors: dict of errors introduced by anonymisation. If
                original_errors is None, all errors found after
                anonymisation are returned, as it's not possible to tell
                which of them pre-existed.

        Raises:
            PixlSkipInstanceError: If dicom-validator raises a RuntimeError
                during validation.
        """
        validator = IODValidator(
            dataset,
            self.dicom_info,
            log_level=logging.ERROR,
        )
        try:
            anon_errors: dict = validator.validate()
        except RuntimeError as error:
            msg = f"dicom-validator raised a RuntimeError when validating the anonymised dataset: {error}"
            raise PixlSkipInstanceError(msg) from error

        if original_errors is None:
            logger.warning(
                "Cannot determine whether validation errors were introduced by "
                "anonymisation, as the original dataset was not validated. "
                "Errors found after anonymisation: {}",
                anon_errors,
            )
            return anon_errors

        diff_errors: dict = {}
        for key in anon_errors:
            if key in original_errors:
                # Keep only errors introduced after the anonymisation
                # The keys of the dictionary containt the actual errors
                diff = set(anon_errors[key]) - set(original_errors[key])
                if diff:
                    diff_errors[key] = diff
            else:
                diff_errors[key] = anon_errors[key]

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
        _logger.debug(line.strip())


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
