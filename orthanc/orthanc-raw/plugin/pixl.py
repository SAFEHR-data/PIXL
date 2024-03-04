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
-OnChange: route stable studies and if auto-routing enabled
-ShouldAutoRoute: checks whether auto-routing is enabled
-OnHeartBeat: extends the REST API
"""
from __future__ import annotations

import logging
import os
from io import BytesIO
from typing import Any

from pydicom import dcmread, Dataset, dcmwrite
from pydicom.tag import Tag
from pydicom.dataset import PrivateBlock

import orthanc

logger = logging.getLogger()
logger.setLevel("DEBUG")


def OnChange(changeType, level, resourceId):  # noqa: ARG001
    """
    # Taken from:
    # https://book.orthanc-server.com/plugins/python.html#auto-routing-studies
    This routes any stable study to a modality named PIXL-Anon if
    ShouldAutoRoute returns true
    """
    if changeType == orthanc.ChangeType.STABLE_STUDY and ShouldAutoRoute():
        print("Stable study: %s" % resourceId)  # noqa: T201
        orthanc.RestApiPost("/modalities/PIXL-Anon/store", resourceId)


def OnHeartBeat(output, uri, **request):  # noqa: ARG001
    """Extends the REST API by registering a new route in the REST API"""
    orthanc.LogWarning("OK")
    output.AnswerBuffer("OK\n", "text/plain")


def ShouldAutoRoute():
    """
    Checks whether ORTHANC_AUTOROUTE_RAW_TO_ANON environment variable is
    set to true or false
    """
    return os.environ.get("ORTHANC_AUTOROUTE_RAW_TO_ANON", "false").lower() == "true"


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


def modify_dicom_tags(receivedDicom: bytes, origin: str) -> Any:
    if origin != orthanc.InstanceOrigin.DICOM_PROTOCOL:
        # don't keep resetting the tag values if this was triggered by an API call!
        print("JES - modify_dicom_tags - doing nothing as triggered by API")
        return orthanc.ReceivedInstanceAction.KEEP_AS_IS, None
    print(f"JES - modify_dicom_tags - entry origin = {origin}")
    print(f"JES - len = {len(receivedDicom)}")
    dataset = dcmread(BytesIO(receivedDicom))
    private_creator_name = "UCLH PIXL"
    # See the orthanc.json config file for where this tag is given a nickname
    private_tag_offset = 0x01
    # LO = Long string max 64, LT = long text max 10240, support paragraphs etc
    # https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html
    vr = "LO"
    unknown_value = "__pixl_unknown_value__"
    group_id = 0x000B
    # The private block is the first free block >= 0x10. Other parts of the code assume
    # it is == 0x10 though :/
    # https://dicom.nema.org/dicom/2013/output/chtml/part05/sect_7.8.html

    print(f"JES - modify_dicom_tags - BEFORE {dataset!s}")
    private_block = dataset.private_block(group_id, private_creator_name, create=True)
    private_block.add_new(private_tag_offset, vr, unknown_value)
    # and try it the slightly different way
    print(f"JES - modify_dicom_tags - AFTER {dataset!s}")
    return orthanc.ReceivedInstanceAction.MODIFY, write_dataset_to_bytes(dataset)
    # return orthanc.ReceivedInstanceAction.KEEP_AS_IS, None
    # return orthanc.ReceivedInstanceAction.DISCARD, None


orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterReceivedInstanceCallback(modify_dicom_tags)
orthanc.RegisterRestCallback("/heart-beat", OnHeartBeat)
