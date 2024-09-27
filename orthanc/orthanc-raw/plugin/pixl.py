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
Facilitates routing of stable studies from orthanc-raw to orthanc-anon

This module provides:
-OnHeartBeat: extends the REST API
"""

from __future__ import annotations

import os
import sys
from io import BytesIO
from typing import TYPE_CHECKING

from core.dicom_tags import DICOM_TAG_PROJECT_NAME, add_private_tag
from decouple import config
from loguru import logger
from pydicom import dcmread

import orthanc
from pixl_dcmd.main import write_dataset_to_bytes
from pixl_dcmd.tagrecording import record_dicom_headers

if TYPE_CHECKING:
    from typing import Any

# Set up logging as main entry point
logger.remove()  # Remove all handlers added so far, including the default one.
logging_level = config("LOG_LEVEL")
if not logging_level:
    logging_level = "INFO"
logger.add(sys.stdout, level=logging_level)

logger.warning("Running logging at level {}", logging_level)


def OnHeartBeat(output, uri, **request):  # noqa: ARG001
    """Extends the REST API by registering a new route in the REST API"""
    orthanc.LogWarning("OK")
    output.AnswerBuffer("OK\n", "text/plain")


def ReceivedInstanceCallback(receivedDicom: bytes, origin: str) -> Any:
    """Optionally record headers from the received DICOM instance."""
    if should_record_headers():
        record_dicom_headers(receivedDicom)
    return modify_dicom_tags(receivedDicom, origin)


def should_record_headers() -> bool:
    """
    Checks whether ORTHANC_RAW_RECORD_HEADERS environment variable is
    set to true or false
    """
    return os.environ.get("ORTHANC_RAW_RECORD_HEADERS", "false").lower() == "true"


def modify_dicom_tags(receivedDicom: bytes, origin: str) -> Any:
    """
    A new incoming DICOM file needs to have the project name private tag added here, so
    that the API will later allow us to edit it.
    However, we don't know its correct value at this point, so just create it with an obvious
    placeholder value.
    """
    if origin != orthanc.InstanceOrigin.DICOM_PROTOCOL:
        # don't keep resetting the tag values if this was triggered by an API call!
        logger.trace("doing nothing as change triggered by API")
        return orthanc.ReceivedInstanceAction.KEEP_AS_IS, None
    dataset = dcmread(BytesIO(receivedDicom))
    # See the orthanc.json config file for where this tag is given a nickname
    # The private block is the first free block >= 0x10.
    # We can't directly control it, but the orthanc config requires it to be
    # hardcoded to 0x10
    # https://dicom.nema.org/dicom/2013/output/chtml/part05/sect_7.8.html

    # Add project name as private tag, at this point, the value is unknown
    private_block = add_private_tag(dataset, DICOM_TAG_PROJECT_NAME)

    logger.debug("added new private block starting at 0x{:04x}", private_block.block_start)
    return orthanc.ReceivedInstanceAction.MODIFY, write_dataset_to_bytes(dataset)


orthanc.RegisterReceivedInstanceCallback(ReceivedInstanceCallback)
orthanc.RegisterRestCallback("/heart-beat", OnHeartBeat)
