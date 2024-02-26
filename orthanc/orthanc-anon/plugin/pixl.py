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

import json
import logging
import os
import threading
import traceback
from io import BytesIO
from time import sleep
from typing import TYPE_CHECKING

import requests
from core import upload
from core.db.queries import get_project_slug_from_hashid
from core.project_config import load_project_config
from decouple import config
from pydicom import dcmread

import orthanc
from pixl_dcmd.main import anonymise_dicom, write_dataset_to_bytes

if TYPE_CHECKING:
    from typing import Any

ORTHANC_USERNAME = config("ORTHANC_USERNAME")
ORTHANC_PASSWORD = config("ORTHANC_PASSWORD")
ORTHANC_URL = "http://localhost:8042"

logger = logging.getLogger(__name__)


def AzureAccessToken():
    """
    Send payload to oath2/token url and
    return the response
    """
    AZ_DICOM_ENDPOINT_CLIENT_ID = config("AZ_DICOM_ENDPOINT_CLIENT_ID")
    AZ_DICOM_ENDPOINT_CLIENT_SECRET = config("AZ_DICOM_ENDPOINT_CLIENT_SECRET")
    AZ_DICOM_ENDPOINT_TENANT_ID = config("AZ_DICOM_ENDPOINT_TENANT_ID")

    url = "https://login.microsoft.com/" + AZ_DICOM_ENDPOINT_TENANT_ID + "/oauth2/token"

    payload = {
        "client_id": AZ_DICOM_ENDPOINT_CLIENT_ID,
        "grant_type": "client_credentials",
        "client_secret": AZ_DICOM_ENDPOINT_CLIENT_SECRET,
        "resource": "https://dicom.healthcareapis.azure.com",
    }

    response = requests.post(url, data=payload, timeout=10)

    return response.json()["access_token"]


TIMER = None


def AzureDICOMTokenRefresh():
    """
    Refresh Azure DICOM token
    If this fails then wait 30s and try again
    If successful then access_token can be used in
    dicomweb_config to update DICOMweb token through API call
    """
    global TIMER
    TIMER = None

    orthanc.LogWarning("Refreshing Azure DICOM token")

    AZ_DICOM_TOKEN_REFRESH_SECS = int(config("AZ_DICOM_TOKEN_REFRESH_SECS"))
    AZ_DICOM_ENDPOINT_NAME = config("AZ_DICOM_ENDPOINT_NAME")
    AZ_DICOM_ENDPOINT_URL = config("AZ_DICOM_ENDPOINT_URL")
    AZ_DICOM_HTTP_TIMEOUT = int(config("HTTP_TIMEOUT"))

    try:
        access_token = AzureAccessToken()
    except Exception:  # noqa: BLE001
        orthanc.LogError(
            "Failed to get an Azure access token. Retrying in 30 seconds\n" + traceback.format_exc()
        )
        sleep(30)
        return AzureDICOMTokenRefresh()

    bearer_str = "Bearer " + access_token

    dicomweb_config = {
        "Url": AZ_DICOM_ENDPOINT_URL,
        "HttpHeaders": {
            "Authorization": bearer_str,
        },
        "HasDelete": True,
        "Timeout": AZ_DICOM_HTTP_TIMEOUT,
    }

    headers = {"content-type": "application/json"}

    url = ORTHANC_URL + "/dicom-web/servers/" + AZ_DICOM_ENDPOINT_NAME

    try:
        requests.put(
            url,
            auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
            headers=headers,
            data=json.dumps(dicomweb_config),
            timeout=10,
        )
    except requests.exceptions.RequestException as e:
        orthanc.LogError("Failed to update DICOMweb token")
        raise SystemExit(e)  # noqa: TRY200, B904

    orthanc.LogWarning("Updated DICOMweb token")

    TIMER = threading.Timer(AZ_DICOM_TOKEN_REFRESH_SECS, AzureDICOMTokenRefresh)
    TIMER.start()
    return None


def Send(resourceId: str) -> None:
    """Send the resource to the appropriate destination"""
    msg = f"Sending {resourceId}"
    logger.debug(msg)

    hashed_patient_id = _get_patient_id(resourceId)
    slug = get_project_slug_from_hashid(hashed_patient_id)
    project_config = load_project_config(slug)

    # send to destination
    if project_config.destination.dicom == "ftps":
        msg = f"Sending {resourceId} via FTPS"
        logger.debug(msg)

        zip_content = _get_study_zip_archive(resourceId)
        upload.FTPSUploader(project_config).upload_dicom_image(zip_content, hashed_patient_id)
    else:
        msg = f"Invalid destination: {project_config.destination.dicom}"
        raise ValueError(msg)


def _get_study_zip_archive(resourceId: str) -> BytesIO:
    # Download zip archive of the DICOM resource
    query = f"{ORTHANC_URL}/studies/{resourceId}/archive"
    fail_msg = "Could not download archive of resource '%s'"
    response_study = _query(resourceId, query, fail_msg)

    # get the zip content
    logger.debug("Downloaded data for resource %s", resourceId)
    return BytesIO(response_study.content)


def SendViaStow(resourceId):
    """
    Makes a POST API call to upload the resource to a dicom-web server
    using orthanc credentials as authorisation
    """
    AZ_DICOM_ENDPOINT_NAME = config("AZ_DICOM_ENDPOINT_NAME")

    url = ORTHANC_URL + "/dicom-web/servers/" + AZ_DICOM_ENDPOINT_NAME + "/stow"

    headers = {"content-type": "application/json"}

    payload = {"Resources": [resourceId], "Synchronous": False}

    logger.debug("Payload: %s", payload)

    try:
        requests.post(
            url,
            auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        msg = f"Sent {resourceId} via STOW"
        logger.info(msg)
    except requests.exceptions.RequestException:
        orthanc.LogError("Failed to send via STOW")


def _get_patient_id(resourceId: str) -> str:
    """
    Queries the Orthanc instance to get the PatientID for a given resource.
    When anonymisation has been applied, the PatientID is the pseudo-anonymised ID.
    """
    query = f"{ORTHANC_URL}/studies/{resourceId}"
    fail_msg = "Could not query study for resource '%s'"

    response_study = _query(resourceId, query, fail_msg)
    json_response = json.loads(response_study.content.decode())
    return str(json_response["PatientMainDicomTags"]["PatientID"])


def _query(resourceId: str, query: str, fail_msg: str) -> requests.Response:
    try:
        response = requests.get(query, auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD), timeout=10)
        success_code = 200
        if response.status_code != success_code:
            raise RuntimeError(fail_msg, resourceId)
    except requests.exceptions.RequestException:
        logger.exception("Failed to query '%s'", resourceId)
    else:
        return response


def ShouldAutoRoute() -> bool:
    """
    Checks whether ORTHANC_AUTOROUTE_ANON_TO_ENDPOINT environment variable is
    set to true or false
    """
    logger.debug("Checking value of autoroute")
    return os.environ.get("ORTHANC_AUTOROUTE_ANON_TO_ENDPOINT", "false").lower() == "true"


def _azure_available() -> bool:
    # Check if AZ_DICOM_ENDPOINT_CLIENT_ID is set
    return config("AZ_DICOM_ENDPOINT_CLIENT_ID", default="") != ""


def OnChange(changeType, level, resource):  # noqa: ARG001
    """
    Three ChangeTypes included in this function:
    - If a study is stable and if ShouldAutoRoute returns true
    then Send is called
    - If orthanc has started then message added to Orthanc LogWarning
    and AzureDICOMTokenRefresh called
    - If orthanc has stopped and TIMER is not none then message added
    to Orthanc LogWarning and TIMER cancelled
    """
    if not ShouldAutoRoute():
        return

    if changeType == orthanc.ChangeType.STABLE_STUDY:
        msg = f"Stable study: {resource}"
        logger.info(msg)
        Send(resource)

    if changeType == orthanc.ChangeType.ORTHANC_STARTED and _azure_available():
        orthanc.LogWarning("Starting the scheduler")
        AzureDICOMTokenRefresh()
    elif changeType == orthanc.ChangeType.ORTHANC_STOPPED:
        if TIMER is not None:
            orthanc.LogWarning("Stopping the scheduler")
            TIMER.cancel()


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

    # Attempt to anonymise and drop the study if any exceptions occur
    try:
        dataset = anonymise_dicom(dataset)
        return orthanc.ReceivedInstanceAction.MODIFY, write_dataset_to_bytes(dataset)
    except Exception:  # noqa: BLE001
        orthanc.LogError("Failed to anonymize study due to\n" + traceback.format_exc())
        return orthanc.ReceivedInstanceAction.DISCARD, None


orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterReceivedInstanceCallback(ReceivedInstanceCallback)
orthanc.RegisterRestCallback("/heart-beat", OnHeartBeat)
