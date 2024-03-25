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

"""
Tag operations for a project. Provides a pydantic model for the tag operations used in
anonymisation together with a loader function.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

import yaml
from pydantic import BaseModel, field_validator

if TYPE_CHECKING:
    from pathlib import Path

    from core.project_config.pixlconfig_model import PixlConfig


class TagScheme(BaseModel):
    """Tag scheme for a single tag operation."""

    tags: list[dict]

    @field_validator("tags")
    @classmethod
    def _valid_tags(cls, tags: list[dict]) -> list[dict]:
        if not isinstance(tags, list):
            msg = "Tags must be a list of dictionaries."
            raise TypeError(msg)
        for tag in tags:
            _check_tag_format(tag)
        return tags


def _check_tag_format(tag: dict) -> None:
    if not isinstance(tag, dict):
        invalid_tag_msg = "Tag must be a dictionary."
        raise TypeError(invalid_tag_msg)
    if "group" not in tag or "element" not in tag:
        invalid_tag_keys_msg = "Tag must have 'group' and 'element' keys."
        raise ValueError(invalid_tag_keys_msg)
    if not isinstance(tag["group"], int) or not isinstance(tag["element"], int):
        invalid_tag_values_msg = "Tag 'group' and 'element' must be integers."
        raise TypeError(invalid_tag_values_msg)


def _load_scheme(tag_operation_file: Path) -> TagScheme | Any:
    yaml_data = yaml.safe_load(tag_operation_file.read_text())
    return TagScheme(tags=yaml_data)


def load_tag_operations(pixl_config: PixlConfig) -> TagOperations:
    """
    Load tag operations for a project.
    :param pixl_config: Project configuration
    """
    base = [_load_scheme(f) for f in pixl_config.tag_operation_files.base]
    manufacturer_overrides = None

    if pixl_config.tag_operation_files.manufacturer_overrides:
        manufacturer_overrides = _load_scheme(
            pixl_config.tag_operation_files.manufacturer_overrides
        )

    return TagOperations(base=base, manufacturer_overrides=manufacturer_overrides)


class TagOperations(BaseModel):
    """
    Tag operations for a project.
    Provides access to the tag operation schemes for a project.

    :param project_config: Project configuration
    :param base: Base tag schemes, can be more than one.
    :param manufacturer_overrides: Manufacturer overrides for tag schemes.
    """

    base: list[TagScheme]
    manufacturer_overrides: Optional[TagScheme]
