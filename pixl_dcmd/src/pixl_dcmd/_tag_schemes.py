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
from typing import Optional

from core.project_config.tag_operations import TagOperations


def merge_tag_schemes(
    tag_operations: TagOperations, manufacturer: Optional[str] = None
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


def _scheme_list_to_dict(tags: list[dict]) -> dict[tuple, dict]:
    """
    Convert a list of tag dictionaries to a dictionary of dictionaries.
    Each group/element pair uniquely identifies a tag.
    """
    return {(tag["group"], tag["element"]): tag for tag in tags}
