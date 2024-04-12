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

from pydicom import Dataset
from logging import getLogger

from core.dicom_tags import DICOM_TAG_PROJECT_NAME

logger = getLogger(__name__)


def get_project_name_as_string(dataset: Dataset) -> str:
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
    return slug
