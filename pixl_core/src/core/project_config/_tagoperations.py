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

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Optional


def _load_scheme(tag_operation_file: Path) -> list[dict]:
    with tag_operation_file.open() as file:
        # Load tag operations scheme from YAML.
        tags = yaml.safe_load(file)
        if not isinstance(tags, list) or not all(isinstance(tag, dict) for tag in tags):
            msg = "Tag operation file must contain a list of dictionaries"
            raise ValueError(msg)
        return tags


def _load_base_tags(base_tags_files: list[Path]) -> dict[tuple, dict]:
    base_tags = [_scheme_list_to_dict(_load_scheme(scheme)) for scheme in base_tags_files]
    merged_tags = {}
    for tags in base_tags:
        merged_tags.update(tags)
    return merged_tags


def _load_manufacturer_overrides(
    manufacturer_overrides_file: Path, manufacturer: Optional[str]
) -> dict[tuple, dict]:
    manufacturer_overrides = _load_scheme(manufacturer_overrides_file)

    # Keep only the overrides for the specified manufacturer
    tag_list = [
        tag
        for override in manufacturer_overrides
        if override["manufacturer"] == manufacturer
        for tag in override["tags"]
    ]
    return _scheme_list_to_dict(tag_list)


def _scheme_list_to_dict(tags: list[dict]) -> dict[tuple, dict]:
    """
    Convert a list of tag dictionaries to a dictionary of dictionaries.
    Each group/element pair uniquely identifies a tag.
    """
    return {(tag["group"], tag["element"]): tag for tag in tags}
