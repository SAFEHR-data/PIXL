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

from io import BytesIO
from logging import getLogger
from os import PathLike
from typing import Any, BinaryIO, Callable, Union

from core.exceptions import PixlSkipMessageError
from core.project_config import load_project_config

from core.dicom_tags import DICOM_TAG_PROJECT_NAME

import requests
from core.project_config import load_tag_operations
from decouple import config
from pydicom import Dataset, dcmwrite
from dicomanonymizer.simpledicomanonymizer import (
    actions_map_name_functions,
    anonymize_dataset,
)

from pixl_dcmd._tag_schemes import merge_tag_schemes
from pixl_dcmd._database import add_hashed_identifier_and_save_to_db, query_db

DicomDataSetType = Union[Union[str, bytes, PathLike[Any]], BinaryIO]

logger = getLogger(__name__)


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


def anonymise_dicom(dataset: Dataset) -> None:
    """
    Anonymises a DICOM dataset as Received by Orthanc in place.
    Finds appropriate configuration based on project name and anonymises by
    - dropping datasets of the wrong modality
    - applying tag operations based on the config file
    - deleting any tags not in the tag scheme
    Returns anonymised dataset.
    """
    raw_slug = dataset.get_private_item(
        DICOM_TAG_PROJECT_NAME.group_id,
        DICOM_TAG_PROJECT_NAME.offset_id,
        DICOM_TAG_PROJECT_NAME.creator_string,
    ).value
    # Get both strings and bytes, which is fun
    if isinstance(raw_slug, bytes):
        logger.debug(f"Bytes slug {raw_slug!r}")
        slug = raw_slug.decode("utf-8").strip()
    else:
        logger.debug(f"String slug '{raw_slug}'")
        slug = raw_slug

    project_config = load_project_config(slug)
    logger.debug(f"Received instance for project {slug}")
    if dataset.Modality not in project_config.project.modalities:
        msg = f"Dropping DICOM Modality: {dataset.Modality}"
        raise PixlSkipMessageError(msg)

    logger.info("Anonymising received instance")

    # Merge tag schemes
    tag_operations = load_tag_operations(project_config)
    tag_scheme = merge_tag_schemes(tag_operations, manufacturer=dataset.Manufacturer)

    modalities = project_config.project.modalities

    logger.info(
        f"Applying DICOM tag anonymisation according to {project_config.tag_operation_files}"
    )
    logger.debug(f"Tag scheme: {tag_scheme}")
    _anonymise_dicom(dataset, tag_scheme, modalities)


def _anonymise_dicom(
    dataset: Dataset, tag_scheme: list[dict], modalities: list[str]
) -> None:
    """
    utility function to anonymise a DICOM dataset in place and facilitate testing
    """

    # Get actions for each tag as functions
    tag_actions = _convert_schema_to_actions(dataset, tag_scheme)

    # Recursively anonymise
    _anonymise_dicom_recursively(dataset, modalities, tag_actions)


def _anonymise_dicom_recursively(
    dataset: Dataset, modalities: list[str], tag_actions: dict[tuple, Callable]
) -> None:
    """
    Recursively anonymise a DICOM dataset in place using an external library, and enforce a whitelist.
    See https://github.com/KitwareMedical/dicom-anonymizer for anonymisation details.
    """
    if (0x0008, 0x0060) in dataset and dataset.Modality not in modalities:
        msg = f"Dropping DICOM Modality: {dataset.Modality}"
        logger.error(msg)
        raise ValueError(msg)

    logger.warning("Anonymising received instance")

    anonymize_dataset(dataset, tag_actions, delete_private_tags=False)

    for elem in dataset.iterall():
        if elem.VR == "SQ":
            for sq_el in elem.value:
                _anonymise_dicom_recursively(sq_el, modalities, tag_actions)
    # Apply whitelist
    _enforce_whitelist(dataset, tag_actions)


def _convert_schema_to_actions(
    dataset: Dataset, tags_list: list[dict]
) -> dict[tuple, Callable]:
    """
    Convert the tag schema to actions (funcitons) for the anonymiser.
    See https://github.com/KitwareMedical/dicom-anonymizer for more details.
    Added custom function secure-hash for linking purposes. This function needs the MRN and
    Accession Number, hence why the dataset is passed in as well.
    """

    # Get the MRN and Accession Number before we've anonymised them
    mrn = dataset[0x0010, 0x0020].value  # Patient ID
    accession_number = dataset[0x0008, 0x0050].value  # Accession Number

    tag_actions = {}
    for tag in tags_list:
        group_el = (tag["group"], tag["element"])
        if tag["op"] == "secure-hash":
            tag_actions[group_el] = lambda _dataset, _tag: _secure_hash(
                _dataset, _tag, mrn, accession_number
            )
            continue
        tag_actions[group_el] = actions_map_name_functions[tag["op"]]

    return tag_actions


def _secure_hash(dataset: Dataset, tag: tuple, mrn: str, accession_number: str) -> None:
    """
    Use the hasher API to consistently but securely hash ids later used for linking.
    """
    grp = tag[0]
    el = tag[1]

    if tag in dataset:
        message = f"Securely hashing: (0x{grp:04x},0x{el:04x})"
        logger.debug(f"\t{message}")
        if grp == 0x0010 and el == 0x0020:  # Patient ID
            pat_value = mrn + accession_number

            hashed_value = _hash_values(pat_value)
            # Query PIXL database
            existing_image = query_db(mrn, accession_number)
            # Insert the hashed_value into the PIXL database
            add_hashed_identifier_and_save_to_db(existing_image, hashed_value)
        elif dataset[grp, el].VR == "SH":
            pat_value = str(dataset[grp, el].value)
            hashed_value = _hash_values(pat_value, 16)

        dataset[grp, el].value = hashed_value

    else:
        message = f"Missing linking variable (0x{grp:04x},0x{el:04x})"
        logger.warning(f"\t{message}")


def _hash_values(pat_value: str, hash_len: int = 0) -> str:
    """
    Utility function for hashing values using the hasher API.
    """
    HASHER_API_AZ_NAME = config("HASHER_API_AZ_NAME")
    HASHER_API_PORT = config("HASHER_API_PORT")
    hasher_req_url = (
        f"http://{HASHER_API_AZ_NAME}:{HASHER_API_PORT}/hash?message={pat_value}"
    )
    if hash_len:
        hasher_req_url += f"&length={hash_len}"
    response = requests.get(hasher_req_url)
    logger.debug("RESPONSE = %s}" % response.text)
    return response.text


def _enforce_whitelist(dataset: Dataset, tags: dict[tuple, Callable]) -> None:
    """Delete any tags not in the tagging schemе in place. Iterates through Sequences."""
    # For every element:
    logger.debug("Enforcing whitelist")
    for de in dataset:
        keep_el = False
        # For every entry in the YAML:
        for group_el in tags:
            grp = group_el[0]
            el = group_el[1]
            op = tags[group_el]

            if de.tag.group == grp and de.tag.element == el:
                if op.__name__ != "delete":
                    keep_el = True

        if not keep_el:
            del_grp = de.tag.group
            del_el = de.tag.element
            del dataset[del_grp, del_el]
            message = "Whitelist - deleting: {name} (0x{grp:04x},0x{el:04x})".format(
                name=de.keyword, grp=del_grp, el=del_el
            )
            logger.debug(f"\t{message}")
