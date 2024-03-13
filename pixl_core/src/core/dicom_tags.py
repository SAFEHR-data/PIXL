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
"""
For defining private DICOM tags.
This information is currently duplicated in
 - pixl_imaging/tests/orthanc_raw_config/orthanc.json
 - orthanc/orthanc-raw/config/orthanc.json
 - projects/configs/tag-operations/test-extract-uclh-omop-cdm.yaml

For now you will have to manually keep these in step.
"""
from dataclasses import dataclass


@dataclass
class PrivateDicomTag:
    """
    Define private DICOM tags that we are using in PIXL.
    We don't specify the private block ID (eg. 0x10) because its value can vary to avoid collisions
    - the private creator string is used to locate the block.
    Unfortunately, Orthanc seems to require you to hardcode it if you want to be able to use
    the API to update the tag value.
    """

    group_id: int
    offset_id: int
    creator_string: str
    tag_nickname: str


DICOM_TAG_PROJECT_NAME = PrivateDicomTag(
    group_id=0x000D,
    offset_id=0x01,
    creator_string="UCLH PIXL",
    tag_nickname="UCLHPIXLProjectName",
)
