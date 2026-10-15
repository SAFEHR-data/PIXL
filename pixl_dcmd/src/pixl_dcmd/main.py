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

import typing
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pydicom
from core.exceptions import PixlSkipInstanceError
from core.project_config import load_image_operations
from core.project_config.pixl_config_model import PixlConfig
from deid.config import DeidRecipe
from deid.dicom.pixels import clean_pixel_data, has_burned_pixels
from dicomanonymizer.simpledicomanonymizer import anonymize_dataset
from loguru import logger
from pydicom import Dataset, dcmread, dcmwrite

from pixl_dcmd._database import (
    get_pseudo_patient_id_and_update_db,
    get_uniq_pseudo_study_uid_and_update_db,
)
from pixl_dcmd._tag_schemes import (
    _convert_schema_to_actions,
    enforce_allowlist,
    get_tag_scheme_and_actions,
)
from pixl_dcmd.dicom_helpers import (
    DicomValidator,
    get_study_info,
)

if typing.TYPE_CHECKING:
    from pixl_dcmd.dicom_helpers import StudyInfo


# See: https://github.com/pydicom/pydicom/issues/2170
pydicom.config.convert_wrong_length_to_UN = True


@dataclass
class StudyAnonymisationState:
    """State shared while anonymising all instances in one study."""

    validation_attempted: bool = False


def write_dataset_to_bytes(dataset: Dataset) -> bytes:
    """
    Write pydicom DICOM dataset to byte array

    Original from:
    https://pydicom.github.io/pydicom/stable/auto_examples/memory_dataset.html
    """
    with BytesIO() as buffer:
        dcmwrite(buffer, dataset)
        buffer.seek(0)
        return buffer.read()


def get_series_to_skip(zipped_study: ZipFile, min_instances: int) -> set[str]:
    """
    Determine which series to skip based on the number of instances in the series.

    If a series has fewer instances than `min_instances`, add it to a set of series to skip.

    Args:
        zipped_study: ZipFile containing the study
        min_instances: Minimum number of instances required to include a series

    """
    if min_instances <= 1:
        return set()

    series_instances = {}
    for file_info in zipped_study.infolist():
        with zipped_study.open(file_info) as file:
            logger.debug("Reading file {}", file)
            dataset = dcmread(
                file,
                stop_before_pixels=True,
                specific_tags=["SeriesInstanceUID"],
            )
            if dataset.SeriesInstanceUID not in series_instances:
                series_instances[dataset.SeriesInstanceUID] = 1
                continue
            series_instances[dataset.SeriesInstanceUID] += 1

    return {
        series for series, count in series_instances.items() if count < min_instances
    }


def _should_exclude_series(dataset: Dataset, cfg: PixlConfig) -> bool:
    """
    Check whether the dataset series should be exlucded based on its description
    and number.
    """
    series_description = dataset.get("SeriesDescription")
    if cfg.is_series_description_excluded(series_description):
        logger.debug("FILTERING OUT series description: {}", series_description)
        return True

    manufacturer = dataset.get("Manufacturer")
    series_number = dataset.get("SeriesNumber")
    if cfg.is_series_number_excluded(
        manufacturer=manufacturer, series_number=series_number
    ):
        logger.debug(
            "FILTERING OUT series number: {} for manufacturer: {}",
            series_number,
            manufacturer,
        )
        return True

    return False


def _should_exclude_manufacturer(dataset: Dataset, cfg: PixlConfig) -> bool:
    manufacturer = dataset.get("Manufacturer")
    if manufacturer is None:
        logger.debug("FILTERING out as manufacturer tag is missing")
        return True

    should_exclude = not cfg.is_manufacturer_allowed(manufacturer=manufacturer)
    if should_exclude:
        logger.debug("FILTERING out manufacturer: {}", manufacturer)
    return should_exclude


def anonymise_dicom_and_update_db(
    dataset: Dataset,
    *,
    config: PixlConfig,
    study_state: StudyAnonymisationState,
) -> dict:
    """
    Anonymise and validate a DICOM dataset, update the PIXL database and return the first intance's validation errors.

    :param dataset: DICOM dataset to be anonymised, updated in place
    :param config: Project config to use for anonymisation
    :param study_state: State of the study anonymisation
    :return: dictionary of validation errors
    """
    identifiable_study_info = get_study_info(dataset)
    _raise_if_should_skip(dataset, config)

    if not study_state.validation_attempted:
        validation_errors = _anonymise_and_validate_included_dicom(dataset, config)
        study_state.validation_attempted = True
    else:
        _anonymise_included_dicom(dataset, config)
        validation_errors = {}

    _generate_pseudo_uids_and_synchronise_pixl_db(
        dataset=dataset,
        project_name=config.project.name,
        identifiable_study_info=identifiable_study_info,
    )
    return validation_errors


def anonymise_and_validate_dicom(
    dataset: Dataset,
    *,
    config: PixlConfig,
) -> dict:
    """
    Anonymise dataset using allow list and compare DICOM validation errors before
    and after anonymising.

    :param dataset: DICOM dataset to be anonymised, updated in place
    :param config: Project config to use for anonymisation
    :return: dictionary of validation errors
    """
    _raise_if_should_skip(dataset, config)
    return _anonymise_and_validate_included_dicom(dataset, config)


def _anonymise_and_validate_included_dicom(
    dataset: Dataset,
    config: PixlConfig,
) -> dict:
    """Anonymise and validate a dataset that passed the project filters."""
    dicom_validator = DicomValidator("2024e")
    original_errors = dicom_validator.validate_original(dataset)

    _anonymise_included_dicom(dataset, config)

    anon_errors = dicom_validator.validate_anonymised(dataset)
    return dicom_validator.get_new_errors(original_errors, anon_errors)


def anonymise_dicom(
    dataset: Dataset,
    config: PixlConfig,
) -> None:
    """
    Anonymises a DICOM dataset as Received by Orthanc in place.
    Finds appropriate configuration based on project name and anonymises by
    - dropping datasets of the wrong modality
    - recursively applying tag operations based on the config file
    - deleting any tags not in the tag scheme recursively

    :param dataset: DICOM dataset to be anonymised, updated in place
    :param config: Project config to use for anonymisation
    """
    _raise_if_should_skip(dataset, config)
    _anonymise_included_dicom(dataset, config)


def _raise_if_should_skip(dataset: Dataset, config: PixlConfig) -> None:
    """Raise when an instance is excluded by the project configuration."""
    if _should_exclude_manufacturer(dataset, config):
        msg = "DICOM instance discarded due to its manufacturer"
        raise PixlSkipInstanceError(msg)
    if _should_exclude_series(dataset, config):
        msg = "DICOM instance discarded due to its series description or number"
        raise PixlSkipInstanceError(msg)
    if dataset.Modality not in config.project.modalities:
        msg = f"Dropping DICOM Modality: {dataset.Modality}"
        raise PixlSkipInstanceError(msg)


def _anonymise_included_dicom(dataset: Dataset, config: PixlConfig) -> None:
    """Anonymise a dataset that passed the project filters."""
    study_info = get_study_info(dataset)
    logger.trace("Anonymising instance for: {}", study_info)

    # Apply any pixel cleaning prior to tag anonymisation
    # Do before anonymisation as some tag operations may rely on pixel data (e.g. burned in pixel detection).
    _clean_dicom_image_pixels(dataset, config)

    tag_scheme, tag_actions = get_tag_scheme_and_actions(
        config,
        str(dataset.Manufacturer),
    )

    logger.debug(
        f"Applying DICOM tag anonymisation according to {config.tag_operation_files}"
    )
    logger.trace(f"Tag scheme: {tag_scheme}")

    enforce_allowlist(dataset, tag_scheme, recursive=True)
    _anonymise_recursively(dataset, tag_actions)


def _clean_dicom_image_pixels(
    dataset: Dataset,
    config: PixlConfig,
) -> None:
    """
    Cleans DICOM image pixels in-place by:
    - locating burned-in pixels based on coordinates within SequenceOfUltrasoundRegions (for US data) given by:
        - RegionLocationMinX0
        - RegionLocationMinY0
        - RegionLocationMaxX1
        - RegionLocationMaxY1
    - see: https://deid.readthedocs.io/en/latest/_modules/deid/dicom/pixels/detect.html#extract_coordinates
    - setting located pixels to zero

    Requires:
        - deid recipe file specified in PixlConfig

    :param dataset: DICOM dataset to cleaned, updated in place
    :param config: Project config to use for pixel cleaning
    """
    study_info = get_study_info(dataset)

    image_operations = load_image_operations(config)
    deid_recipe_paths = image_operations.deid_recipes
    if not deid_recipe_paths:
        logger.trace(
            "No deid recipe provided for pixel cleaning, skipping pixel cleaning."
        )
        return

    deid_recipe = _get_deid_recipe(tuple(deid_recipe_paths))
    logger.debug(f"Cleaning pixels for project {config.project.name}:  {study_info}")
    burned_pixels = has_burned_pixels(dataset, deid=deid_recipe)
    cleaned_pixels = clean_pixel_data(dicom_file=dataset, results=burned_pixels)

    pixel_bytes = cleaned_pixels.tobytes()
    if dataset.file_meta.TransferSyntaxUID.is_compressed:
        dataset.PixelData = pydicom.encaps.encapsulate([pixel_bytes])
    else:
        dataset.PixelData = pixel_bytes


@lru_cache(maxsize=100)
def _get_deid_recipe(recipe_paths: tuple[Path, ...]) -> DeidRecipe:
    """Parse each set of de-identification recipes once per process."""
    return DeidRecipe(list(recipe_paths))


def _anonymise_dicom_from_scheme(
    dataset: Dataset,
    project_slug: str,
    tag_scheme: list[dict],
) -> None:
    """
    Converts tag scheme to tag actions and calls _anonymise_recursively.
    """
    tag_actions = _convert_schema_to_actions(project_slug, tag_scheme)

    _anonymise_recursively(dataset, tag_actions)


def _anonymise_recursively(
    dataset: Dataset, tag_actions: dict[tuple, typing.Callable]
) -> None:
    """
    Anonymises a DICOM dataset recursively (for items in sequences) in place.
    """
    anonymize_dataset(dataset, tag_actions, delete_private_tags=False)
    for de in dataset:
        if de.VR == "SQ":
            for item in de.value:
                _anonymise_recursively(item, tag_actions)


def parse_validation_results(results: dict) -> str:
    """Parse the validation results into a human-readable string."""
    res_str = ""
    for key, value in results.items():
        res_str += f"{key}: {value}\n"
    return res_str


def _generate_pseudo_uids_and_synchronise_pixl_db(
    dataset: Dataset,
    project_name: str,
    identifiable_study_info: StudyInfo,
) -> None:
    """
    Synchronise the anonymisation with the pixl database.

    If the pixl database has a value for set for the pseudo identifier, then update the
    DICOM data with the value, otherwise save the anonymised data from the DICOM dataset
    to the pixl database.

    - pseudo_study_uid -> DICOM study uid tag
    - pseudo_patient_id -> DICOM patient identifier tag
    """
    dataset[0x0020, 0x000D].value = get_uniq_pseudo_study_uid_and_update_db(
        project_name,
        identifiable_study_info,
    )

    anonymised_study_info = get_study_info(dataset)
    dataset[0x0010, 0x0020].value = get_pseudo_patient_id_and_update_db(
        project_name,
        identifiable_study_info,
        anonymised_study_info.mrn,
    )
