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
Applies anonymisation scheme to datasets

This module:
-Modifies a DICOM instance received by Orthanc and applies anonymisation
-Upload the resource to a dicom-web server
"""

from __future__ import annotations

import logging
import os
import traceback
from io import BytesIO
from typing import TYPE_CHECKING

import requests
from core.exceptions import PixlSkipMessageError
from pydicom import dcmread

import orthanc
from pixl_dcmd.main import anonymise_dicom, should_exclude_series, write_dataset_to_bytes

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


def Send(study_id: str) -> None:
    """
    Send the resource to the appropriate destination.
    Throws an exception if the image has already been exported.
    """
    msg = f"Sending {study_id}"
    logger.debug(msg)
    notify_export_api_of_readiness(study_id)


EXPORT_API_URL = "http://ehr-api:8000"


def notify_export_api_of_readiness(study_id: str):
    """XXX: make the /export-dicom-from-orthanc API call to export-api"""
    url = EXPORT_API_URL + "/export-dicom-from-orthanc"
    payload = {"study_id": study_id}
    response = requests.post(url, data=payload, timeout=30)
    response.raise_for_status()


def should_auto_route() -> bool:
    """
    Checks whether ORTHANC_AUTOROUTE_ANON_TO_ENDPOINT environment variable is
    set to true or false
    """
    logger.debug("Checking value of autoroute")
    return os.environ.get("ORTHANC_AUTOROUTE_ANON_TO_ENDPOINT", "false").lower() == "true"


def OnChange(changeType, level, resource):  # noqa: ARG001
    """
    If a study is stable and if should_auto_route returns true
    then notify the export API that it should perform the upload of DICOM data.
    """
    if not should_auto_route():
        return

    if changeType == orthanc.ChangeType.STABLE_STUDY:
        msg = f"Stable study: {resource}"
        logger.info(msg)
        Send(resource)


def OnHeartBeat(output, uri, **request) -> Any:  # noqa: ARG001
    """Extends the REST API by registering a new route in the REST API"""
    orthanc.LogInfo("OK")
    output.AnswerBuffer("OK\n", "text/plain")


def ReceivedInstanceCallback(receivedDicom: bytes, origin: str) -> Any:
    """Modifies a DICOM instance received by Orthanc and applies anonymisation."""
    if origin == orthanc.InstanceOrigin.REST_API:
        orthanc.LogWarning("DICOM instance received from the REST API")
    elif origin == orthanc.InstanceOrigin.DICOM_PROTOCOL:
        orthanc.LogWarning("DICOM instance received from the DICOM protocol")

    # Read the bytes as DICOM/
    dataset = dcmread(BytesIO(receivedDicom))

    # Do before anonymisation in case someone decides to delete the
    # Series Description tag as part of anonymisation.
    if should_exclude_series(dataset):
        orthanc.LogWarning("DICOM instance discarded due to its series description")
        return orthanc.ReceivedInstanceAction.DISCARD, None

    # Attempt to anonymise and drop the study if any exceptions occur
    try:
        dataset = anonymise_dicom(dataset)
        return orthanc.ReceivedInstanceAction.MODIFY, write_dataset_to_bytes(dataset)
    except PixlSkipMessageError as error:
        logger.debug("Skipping instance: %s", error)
        return orthanc.ReceivedInstanceAction.DISCARD, None
    except Exception:  # noqa: BLE001
        orthanc.LogError("Failed to anonymize instance due to\n" + traceback.format_exc())
        return orthanc.ReceivedInstanceAction.DISCARD, None


orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterReceivedInstanceCallback(ReceivedInstanceCallback)
orthanc.RegisterRestCallback("/heart-beat", OnHeartBeat)
