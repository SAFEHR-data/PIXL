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

from pathlib import Path

import pytest
import pytest_check
from core.project_config import load_project_config
from core.project_config.tag_operations import TagOperations, load_tag_operations
from decouple import config
from pixl_dcmd._tag_schemes import merge_tag_schemes

PROJECT_CONFIGS_DIR = Path(config("PROJECT_CONFIGS_DIR"))
TEST_CONFIG = "test-extract-uclh-omop-cdm"


@pytest.fixture()
def base_only_tag_scheme() -> TagOperations:
    project_config = load_project_config(TEST_CONFIG)
    project_config.tag_operation_files.manufacturer_overrides = None
    return load_tag_operations(project_config)


def test_merge_base_only_tags(base_only_tag_scheme):
    """
    GIVEN TagOperations with only a base file
    WHEN the tag schemes are merged
    THEN the result should be the same as the base file
    """
    tags = merge_tag_schemes(base_only_tag_scheme)
    expected = [tag for base in base_only_tag_scheme.base for tag in base]
    count_tags = dict()
    for tag in expected:
        key = f"{tag['group']:04x},{tag['element']:04x}"
        if key in count_tags:
            count_tags[key] += 1
        else:
            count_tags[key] = 1

    for key, values in count_tags.items():
        pytest_check.equal(
            values, 1, msg=f"{key} is replicated please check config files to remove it"
        )

    assert tags == expected


def test_merge_all_tags():
    """
    GIVEN A project config defining tag operations from a base file and manufacturer overrides
    WHEN the tag schemes are merged
    THEN the tag schemes should be merged without error
    """
    project_config = load_project_config(TEST_CONFIG)
    tag_operations = load_tag_operations(project_config)
    assert merge_tag_schemes(tag_operations)


@pytest.fixture()
def tag_ops_with_manufacturer_overrides(tmp_path_factory):
    """
    TagOperations with a base file and manufacturer overrides, where the base file has 3 tags
    and the manufacturer overrides ovverrides 1 of them and has 2 extra tags.
    This is intetnionally not added in conftest.py because the `PROJECT_CONFIG_DIR` envvar nees to
    be set before importing core.project_config.TagOperations.
    """
    base_tags = [
        {"name": "tag1", "group": 0x001, "element": 0x1000, "op": "delete"},
        {"name": "tag2", "group": 0x002, "element": 0x1001, "op": "delete"},
        {"name": "tag3", "group": 0x003, "element": 0x1002, "op": "delete"},
    ]
    manufacturer_overrides_tags = [
        [
            {
                "manufacturer": "manufacturer_1",
                "tags": [
                    # Override tag1 for manufacturer 1
                    {"name": "tag1", "group": 0x001, "element": 0x1000, "op": "keep"},
                    {"name": "tag4", "group": 0x004, "element": 0x1011, "op": "delete"},
                ],
            },
            {
                "manufacturer": "manufacturer_2",
                "tags": [
                    {"name": "tag6", "group": 0x006, "element": 0x1100, "op": "keep"},
                    {"name": "tag7", "group": 0x007, "element": 0x1111, "op": "delete"},
                    # Override tag3 for manufacturer 2
                    {"name": "tag3", "group": 0x003, "element": 0x1002, "op": "keep"},
                ],
            },
        ],
        [
            {
                "manufacturer": "manufacturer_1",
                "tags": [
                    # Override tag1 for manufacturer 1
                    {"name": "tag5", "group": 0x005, "element": 0x1012, "op": "delete"},
                ],
            },
        ],
    ]

    return TagOperations(
        base=[base_tags], manufacturer_overrides=manufacturer_overrides_tags
    )


def test_manufacturer_overrides_tag_scheme(tag_ops_with_manufacturer_overrides):
    """
    GIVEN TagOperations with a base file and manufacturer overrides, where the base file has 3 tags
        and the manufacturer overrides ovverrides 1 of them and has 2 extra tags
    WHEN the tag schemes are merged
    THEN the result should be the base file with the manufacturer overrides applied
    """
    tags = merge_tag_schemes(
        tag_ops_with_manufacturer_overrides, manufacturer="manufacturer_1"
    )

    # Check that we have the tags
    assert len(tags) == 5
    assert [tag["name"] for tag in tags] == ["tag1", "tag2", "tag3", "tag4", "tag5"]

    # Check that the overridden tag has the correct value
    overridden_tag = next(tag for tag in tags if tag["name"] == "tag1")
    assert overridden_tag["op"] == "keep"
