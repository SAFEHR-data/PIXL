#  Copyright (c) University College London Hospitals NHS Foundation Trust
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
"""Study-level anonymisation suitable for ProcessPoolExecutor workers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO
from zipfile import ZipFile

from core.exceptions import PixlDiscardError, PixlSkipInstanceError
from core.project_config.pixl_config_model import load_project_config
from loguru import logger
from pydicom import dcmread

from pixl_dcmd.dicom_helpers import StudyInfo
from pixl_dcmd.main import (
    anonymise_dicom_and_update_db,
    get_series_to_skip,
    parse_validation_results,
    write_dataset_to_bytes,
)


@dataclass(frozen=True)
class InstanceDeidentificationFailure:
    """Details of a skipped/failed instance for metrics recording in the parent process."""

    failure_type: str
    message: str


@dataclass(frozen=True)
class AnonymiseStudyResult:
    """Picklable result of anonymising all instances in a study zip."""

    instances_bytes: list[bytes]
    anonymised_study_uid: str
    skipped_instance_counts: dict[str, int]
    dicom_validation_errors: dict
    instance_failures: list[InstanceDeidentificationFailure]


def anonymise_study_zip(
    zipped_study_bytes: bytes,
    project_name: str,
    series_to_keep: list[str],
    study_info: StudyInfo,
) -> AnonymiseStudyResult:
    """
    Anonymise every instance in a study zip archive.

    Designed to run in a spawned subprocess so CPU-bound work is not limited by the
    Orthanc plugin process GIL. Must not import or call the Orthanc Python API.
    """
    config = load_project_config(project_name)
    with ZipFile(BytesIO(zipped_study_bytes)) as zipped_study:
        series_to_skip = get_series_to_skip(
            zipped_study, config.min_instances_per_series
        )
        anonymised_instances_bytes: list[bytes] = []
        skipped_instance_counts: dict[str, int] = defaultdict(int)
        dicom_validation_errors: dict = {}
        instance_failures: list[InstanceDeidentificationFailure] = []
        anonymised_study_uid: str | None = None

        for file_info in zipped_study.infolist():
            with zipped_study.open(file_info) as file:
                logger.debug("Reading file {}", file)
                dataset = dcmread(file)

                if series_to_keep and dataset.SeriesInstanceUID not in series_to_keep:
                    logger.debug(
                        "Skipping series {} for study {} as series not in series_to_keep",
                        dataset.SeriesInstanceUID,
                        study_info,
                    )
                    key = "DICOM instance discarded as series not requested"
                    skipped_instance_counts[key] += 1
                    instance_failures.append(
                        InstanceDeidentificationFailure(
                            failure_type="PixlSkipSeriesError",
                            message=key,
                        )
                    )
                    continue

                if dataset.SeriesInstanceUID in series_to_skip:
                    logger.debug(
                        "Skipping series {} for study {} due to too few instances",
                        dataset.SeriesInstanceUID,
                        study_info,
                    )
                    key = "DICOM instance discarded as series has too few instances"
                    skipped_instance_counts[key] += 1
                    instance_failures.append(
                        InstanceDeidentificationFailure(
                            failure_type="PixlSkipSeriesError",
                            message=key,
                        )
                    )
                    continue

                try:
                    validation_errors = anonymise_dicom_and_update_db(
                        dataset, config=config
                    )
                    anonymised_instance = write_dataset_to_bytes(dataset)
                except PixlSkipInstanceError as e:
                    logger.debug(
                        "Skipping instance {} for {}: {}",
                        dataset[0x0008, 0x0018].value,
                        study_info,
                        e,
                    )
                    skipped_instance_counts[str(e)] += 1
                    instance_failures.append(
                        InstanceDeidentificationFailure(
                            failure_type="PixlSkipInstanceError",
                            message=str(e),
                        )
                    )
                else:
                    anonymised_instances_bytes.append(anonymised_instance)
                    anonymised_study_uid = dataset[0x0020, 0x000D].value
                    dicom_validation_errors |= validation_errors

    if not anonymised_instances_bytes or anonymised_study_uid is None:
        message = f"All instances have been skipped for study: {dict(skipped_instance_counts)}"
        raise PixlDiscardError(message)

    with logger.contextualize(pseudo_study_uid=anonymised_study_uid):
        logger.debug(
            "Project '{}' {}, skipped instances: {}",
            project_name,
            study_info,
            dict(skipped_instance_counts),
        )

        if dicom_validation_errors:
            logger.warning(
                "The anonymisation introduced the following validation errors:\n{}",
                parse_validation_results(dicom_validation_errors),
            )
        logger.success(
            "Finished anonymising project: '{}', {}", project_name, study_info
        )

    return AnonymiseStudyResult(
        instances_bytes=anonymised_instances_bytes,
        anonymised_study_uid=anonymised_study_uid,
        skipped_instance_counts=dict(skipped_instance_counts),
        dicom_validation_errors=dicom_validation_errors,
        instance_failures=instance_failures,
    )
