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
from io import BytesIO

import requests
from core.exceptions import PixlDiscardError
from core.project_config import load_project_config, load_tag_operations
from decouple import config
from dicomanonymizer.simpledicomanonymizer import (
    actions_map_name_functions,
    anonymize_dataset,
)
from loguru import logger
from pydicom import DataElement, Dataset, dcmwrite

from core.project_config.pixl_config_model import PixlConfig, load_config_and_validate
from pixl_dcmd._database import (
    get_uniq_pseudo_study_uid_and_update_db,
    get_pseudo_patient_id_and_update_db,
)
from pixl_dcmd._dicom_helpers import (
    DicomValidator,
    get_project_name_as_string,
    get_study_info,
)
from pixl_dcmd._tag_schemes import _scheme_list_to_dict, merge_tag_schemes

if typing.TYPE_CHECKING:
    from pathlib import Path


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


def _should_exclude_series(dataset: Dataset, cfg: PixlConfig) -> bool:
    series_description = dataset.get("SeriesDescription")
    if cfg.is_series_excluded(series_description):
        logger.info("FILTERING OUT series description: {}", series_description)
        return True
    return False


def anonymise_and_validate_dicom(
    dataset: Dataset,
    *,
    config_path: Path | None = None,
    synchronise_pixl_db: bool = True,
) -> dict:
    """
    Anonymise dataset using allow list and compare DICOM validation errors before
    and after anonymising.

    If synchronise_pixl_db is True, then synchronise with the pixl database.
    If the pixl database has a value for set for the pseudo identifier, then update the
    DICOM data with the value, otherwise save the anonymised data from the DICOM dataset
    to the pixl database.
    - pseudo_study_uid -> DICOM study uid tag
    - pseudo_patient_id -> DICOM patient identifier tag

    :param dataset: DICOM dataset to be anonymised, updated in place
    :param config_path: path to config, for external users.
      if not set then this will be determined using the PIXL project tag in the DICOM
    :param synchronise_pixl_db: synchronise the anonymisation with the pixl database
    :return: dictionary of validation errors
    """
    # Set up Dicom validator and validate the original dataset
    dicom_validator = DicomValidator(edition="current")
    dicom_validator.validate_original(dataset)

    anonymise_dicom(
        dataset, config_path=config_path, synchronise_pixl_db=synchronise_pixl_db
    )

    # Validate the anonymised dataset
    validation_errors = dicom_validator.validate_anonymised(dataset)
    if validation_errors:
        logger.warning(
            "The anonymisation introduced the following validation errors:\n{}",
            _parse_validation_results(validation_errors),
        )
    return validation_errors


def anonymise_dicom(
    dataset: Dataset, config_path: Path | None = None, synchronise_pixl_db: bool = True
) -> None:
    """
    Anonymises a DICOM dataset as Received by Orthanc in place.
    Finds appropriate configuration based on project name and anonymises by
    - dropping datasets of the wrong modality
    - recursively applying tag operations based on the config file
    - deleting any tags not in the tag scheme recursively

    If synchronise_pixl_db is True, then synchronise with the pixl database.
    If the pixl database has a value for set for the pseudo identifier, then update the
    DICOM data with the value, otherwise save the anonymised data from the DICOM dataset
    to the pixl database.
    - pseudo_study_uid -> DICOM study uid tag
    - pseudo_patient_id -> DICOM patient identifier tag

    :param dataset: DICOM dataset to be anonymised, updated in place
    :param config_path: path to config, for external users.
      if not set then this will be determined using the PIXL project tag in the DICOM
    :param synchronise_pixl_db: synchronise the anonymisation with the pixl database
    """

    study_info = get_study_info(dataset)

    if config_path:
        project_config = load_config_and_validate(config_path)
        project_name = project_config.project.name
    else:
        project_name = get_project_name_as_string(dataset)
        project_config = load_project_config(project_name)
    logger.debug(f"Processing instance for project {project_name}:  {study_info}")

    # Do before anonymisation in case someone decides to delete the
    # Series Description tag as part of anonymisation.
    if _should_exclude_series(dataset, project_config):
        msg = "DICOM instance discarded due to its series description"
        raise PixlDiscardError(msg)
    if dataset.Modality not in project_config.project.modalities:
        msg = f"Dropping DICOM Modality: {dataset.Modality}"
        raise PixlDiscardError(msg)

    logger.info("Anonymising received instance: {}", study_info)

    # Merge tag schemes
    tag_operations = load_tag_operations(project_config)
    tag_scheme = merge_tag_schemes(tag_operations, manufacturer=dataset.Manufacturer)

    logger.debug(
        f"Applying DICOM tag anonymisation according to {project_config.tag_operation_files}"
    )
    logger.trace(f"Tag scheme: {tag_scheme}")

    _enforce_allowlist(dataset, tag_scheme, recursive=True)
    _anonymise_dicom_from_scheme(dataset, project_name, tag_scheme)

    if synchronise_pixl_db:
        # Update the dataset with the new pseudo study ID
        dataset[0x0020, 0x000D].value = get_uniq_pseudo_study_uid_and_update_db(
            project_name, study_info
        )
        anonymise_study_info = get_study_info(dataset)
        dataset[0x0010, 0x0020].value = get_pseudo_patient_id_and_update_db(
            project_name, study_info, anonymise_study_info.mrn
        )  # type: ignore[func-returns-value]


def _anonymise_dicom_from_scheme(
    dataset: Dataset,
    project_slug: str,
    tag_scheme: list[dict],
) -> None:
    """
    Converts tag scheme to tag actions and calls _anonymise_recursively.
    """
    tag_actions = _convert_schema_to_actions(dataset, project_slug, tag_scheme)

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


def _convert_schema_to_actions(
    dataset: Dataset, project_slug: str, tags_list: list[dict]
) -> dict[tuple, typing.Callable]:
    """
    Convert the tag schema to actions (funcitons) for the anonymiser.
    See https://github.com/KitwareMedical/dicom-anonymizer for more details.
    Added custom function secure-hash for linking purposes. This function needs the MRN and
    Accession Number, hence why the dataset is passed in as well.
    """

    tag_actions = {}
    for tag in tags_list:
        group_el = (tag["group"], tag["element"])
        if tag["op"] == "secure-hash":
            tag_actions[group_el] = lambda _dataset, _tag: _secure_hash(
                _dataset, project_slug, _tag
            )
            continue
        tag_actions[group_el] = actions_map_name_functions[tag["op"]]

    return tag_actions


def _secure_hash(
    dataset: Dataset,
    project_slug: str,
    tag: tuple,
) -> None:
    """
    Use the hasher API to consistently but securely hash ids later used for linking.
    """
    grp = tag[0]
    el = tag[1]

    if tag in dataset:
        message = f"Securely hashing: (0x{grp:04x},0x{el:04x})"
        logger.debug(f"\t{message}")
        if dataset[grp, el].VR == "LO":
            pat_value = str(dataset[grp, el].value)
            hashed_value = _hash_values(pat_value, project_slug, hash_len=64)
        else:
            # This is because we currently only hash patient id specifically.
            # Other types can be added easily if needed.
            raise PixlDiscardError(f"Tag {tag} is not an LO VR type, cannot hash.")

        dataset[grp, el].value = hashed_value


def _hash_values(pat_value: str, project_slug: str, hash_len: int = 0) -> str:
    """
    Utility function for hashing values using the hasher API.
    """
    HASHER_API_AZ_NAME = config("HASHER_API_AZ_NAME")
    HASHER_API_PORT = config("HASHER_API_PORT")
    hasher_req_url = f"http://{HASHER_API_AZ_NAME}:{HASHER_API_PORT}/hash"
    request_params: dict[str, str | int] = {
        "project_slug": project_slug,
        "message": pat_value,
    }
    if hash_len:
        request_params["length"] = hash_len

    response = requests.get(hasher_req_url, params=request_params)
    logger.debug("RESPONSE = {}", response.text)
    return response.text


def _enforce_allowlist(
    dataset: Dataset, tag_scheme: list[dict], recursive: bool
) -> None:
    """
    Enforce the allowlist on the dataset.
    """
    dataset.walk(lambda ds, de: _allowlist_tag(ds, de, tag_scheme), recursive)


def _allowlist_tag(dataset: Dataset, de: DataElement, tag_scheme: list[dict]) -> None:
    """Delete element if it is not in the tagging schemе."""
    tag_dict = _scheme_list_to_dict(tag_scheme)
    if (de.tag.group, de.tag.element) in tag_dict and tag_dict[
        (de.tag.group, de.tag.element)
    ]["op"] != "delete":
        return
    del dataset[de.tag]


def _parse_validation_results(results: dict) -> str:
    """Parse the validation results into a human-readable string."""
    res_str = ""
    for key, value in results.items():
        res_str += f"{key}: {value}\n"
    return res_str
