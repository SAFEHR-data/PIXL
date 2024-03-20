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
    the API to update the tag value. So we have to take what we're given and log an error if
    it's not 0x10.
    """

    PLACEHOLDER_VALUE = "__pixl_unknown_value__"

    group_id: int
    offset_id: int
    required_private_block: int
    creator_string: str
    tag_nickname: str

    def acceptable_private_block(self, actual_private_block: int) -> bool:
        """
        Detect whether the private block given to us is acceptable
        :param actual_private_block: one byte private block ID
        """
        if not 0x10 <= actual_private_block <= 0xFF:  # noqa: PLR2004 see DICOM spec
            err_str = f"private block must be from 0x10 to 0xff, got {actual_private_block}"
            raise ValueError(err_str)
        if self.required_private_block is None:
            return True
        return self.required_private_block == actual_private_block


DICOM_TAG_PROJECT_NAME = PrivateDicomTag(
    group_id=0x000D,
    required_private_block=0x10,
    offset_id=0x01,
    creator_string="UCLH PIXL",
    tag_nickname="UCLHPIXLProjectName",
)
