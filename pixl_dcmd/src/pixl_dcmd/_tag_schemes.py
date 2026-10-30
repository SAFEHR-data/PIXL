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

"""Helpers to handle tag operations for anonymisation."""

from __future__ import annotations

import re
from collections.abc import Callable
from functools import lru_cache
from typing import TYPE_CHECKING

import requests
from core.exceptions import PixlSkipInstanceError
from core.project_config.tag_operations import TagOperations, _load_tag_operations
from decouple import config
from dicomanonymizer.simpledicomanonymizer import ActionsMapNameFunctions
from loguru import logger


if TYPE_CHECKING:
    from pathlib import Path
    from pydicom import Dataset
    from pydicom.dataelem import DataElement

    from core.project_config.pixl_config_model import PixlConfig


def merge_tag_schemes(
    tag_operations: TagOperations, manufacturer: str | None = None
) -> list[dict]:
    """Merge multiple tag schemes into a single scheme."""
    all_tags = {}

    # Merge base tag schemes
    for base_tags in tag_operations.base:
        all_tags.update(_scheme_list_to_dict(base_tags))

    if tag_operations.manufacturer_overrides and manufacturer:
        for override_file in tag_operations.manufacturer_overrides:
            manufacturer_tags = [
                tag
                for override in override_file
                if re.search(override["manufacturer"], manufacturer, re.IGNORECASE)
                for tag in override["tags"]
            ]
            all_tags.update(_scheme_list_to_dict(manufacturer_tags))

    return list(all_tags.values())


def get_tag_scheme_and_actions(
    config: PixlConfig,
    manufacturer: str,
) -> tuple[list[dict], dict[tuple, Callable]]:
    """Get cached tag operations for a project's manufacturer."""
    return _get_tag_scheme_and_actions(
        config.project.name,
        tuple(config.tag_operation_files.base),
        tuple(config.tag_operation_files.manufacturer_overrides or ()),
        manufacturer,
    )


@lru_cache(maxsize=100)
def _get_tag_scheme_and_actions(
    project_slug: str,
    base_files: tuple[Path, ...],
    manufacturer_override_files: tuple[Path, ...],
    manufacturer: str,
) -> tuple[list[dict], dict[tuple, Callable]]:
    """Build a project's tag scheme and actions once per manufacturer."""
    tag_operations = _load_tag_operations(base_files, manufacturer_override_files)
    tag_scheme = merge_tag_schemes(
        tag_operations,
        manufacturer=manufacturer,
    )
    tag_actions = _convert_schema_to_actions(project_slug, tag_scheme)
    return tag_scheme, tag_actions


def _convert_schema_to_actions(
    project_slug: str,
    tags_list: list[dict],
) -> dict[tuple, Callable]:
    """Convert a tag schema to dicom-anonymizer actions."""
    tag_actions = {}
    for tag in tags_list:
        group_el = (tag["group"], tag["element"])
        if tag["op"] == "secure-hash":
            tag_actions[group_el] = lambda dataset, dicom_tag: _secure_hash(
                dataset,
                project_slug,
                dicom_tag,
            )
            continue
        tag_actions[group_el] = ActionsMapNameFunctions[tag["op"]].value.function

    return tag_actions


def _secure_hash(
    dataset: Dataset,
    project_slug: str,
    tag: tuple,
) -> None:
    """Securely hash a supported DICOM tag using the hasher API."""
    group, element = tag
    if tag not in dataset:
        return

    logger.trace(f"Securely hashing: (0x{group:04x},0x{element:04x})")
    if dataset[group, element].VR != "LO":
        msg = f"Tag {tag} is not an LO VR type, cannot hash."
        raise PixlSkipInstanceError(msg)

    patient_value = str(dataset[group, element].value)
    dataset[group, element].value = _hash_values(
        patient_value,
        project_slug,
        hash_len=64,
    )


@lru_cache(maxsize=1000)
def _hash_values(patient_value: str, project_slug: str, hash_len: int = 0) -> str:
    """Hash a value using the project-specific hasher API."""
    hasher_api_name = config("HASHER_API_AZ_NAME")
    hasher_api_port = config("HASHER_API_PORT")
    hasher_url = f"http://{hasher_api_name}:{hasher_api_port}/hash"
    request_params: dict[str, str | int] = {
        "project_slug": project_slug,
        "message": patient_value,
    }
    if hash_len:
        request_params["length"] = hash_len

    response = requests.get(hasher_url, params=request_params)
    logger.debug("RESPONSE = {}", response.text)
    return response.text


def enforce_allowlist(
    dataset: Dataset, tag_scheme: list[dict], recursive: bool
) -> None:
    """
    Enforce the allowlist on the dataset.
    """
    tag_dict = _scheme_list_to_dict(tag_scheme)
    dataset.walk(lambda ds, de: _allowlist_tag(ds, de, tag_dict), recursive)


def _scheme_list_to_dict(tags: list[dict]) -> dict[tuple, dict]:
    """
    Convert a list of tag dictionaries to a dictionary of dictionaries.
    Each group/element pair uniquely identifies a tag.
    """
    return {(tag["group"], tag["element"]): tag for tag in tags}


def _allowlist_tag(
    dataset: Dataset, de: DataElement, tag_dict: dict[tuple, dict]
) -> None:
    """Delete element if it is not in the tagging schemе."""
    if (de.tag.group, de.tag.element) in tag_dict and tag_dict[
        (de.tag.group, de.tag.element)
    ]["op"] != "delete":
        return
    del dataset[de.tag]
