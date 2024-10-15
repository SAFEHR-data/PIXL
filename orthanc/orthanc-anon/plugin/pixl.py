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
import os
import sys
import threading
import traceback
from io import BytesIO
from time import sleep
from typing import TYPE_CHECKING, cast
from zipfile import ZipFile

import pydicom
import requests
from core.exceptions import PixlDiscardError
from decouple import config
from loguru import logger
from pydicom import dcmread

import orthanc
from pixl_dcmd._dicom_helpers import DicomValidator, get_study_info
from pixl_dcmd.main import (
    anonymise_and_validate_dicom,
    write_dataset_to_bytes,
)

if TYPE_CHECKING:
    from typing import Any

ORTHANC_USERNAME = config("ORTHANC_USERNAME")
ORTHANC_PASSWORD = config("ORTHANC_PASSWORD")
ORTHANC_URL = "http://localhost:8042"

EXPORT_API_URL = "http://export-api:8000"

# Set up logging as main entry point
logger.remove()  # Remove all handlers added so far, including the default one.
logging_level = config("LOG_LEVEL")
if not logging_level:
    logging_level = "INFO"
logger.add(sys.stdout, level=logging_level)

logger.warning("Running logging at level {}", logging_level)

# Force the spec to be downloaded on startup
DicomValidator(edition="current")


def AzureAccessToken() -> str:
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

    response_json = response.json()
    # We may wish to make use of the "expires_in" (seconds) value
    # to refresh this token less aggressively
    return cast(str, response_json["access_token"])


TIMER = None


def AzureDICOMTokenRefresh() -> None:
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
            # downstream auth token
            "Authorization": bearer_str,
        },
        "HasDelete": True,
        "Timeout": AZ_DICOM_HTTP_TIMEOUT,
    }

    headers = {"content-type": "application/json"}

    url = ORTHANC_URL + "/dicom-web/servers/" + AZ_DICOM_ENDPOINT_NAME
    # dynamically defining an DICOMWeb endpoint in Orthanc

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


def Send(study_id: str) -> None:
    """
    Send the resource to the appropriate destination.
    Throws an exception if the image has already been exported.
    """
    msg = f"Sending {study_id}"
    logger.debug(msg)
    notify_export_api_of_readiness(study_id)


def notify_export_api_of_readiness(study_id: str):
    """
    Tell export-api that our data is ready and it should download it from us and upload
    as appropriate
    """
    url = EXPORT_API_URL + "/export-dicom-from-orthanc"
    payload = {"study_id": study_id}
    timeout: float = config("PIXL_DICOM_TRANSFER_TIMEOUT", default=180, cast=float)
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()


def should_export() -> bool:
    """
    Checks whether ORTHANC_AUTOROUTE_ANON_TO_ENDPOINT environment variable is
    set to true or false
    """
    logger.trace("Checking value of autoroute")
    return os.environ.get("ORTHANC_AUTOROUTE_ANON_TO_ENDPOINT", "false").lower() == "true"


def _azure_available() -> bool:
    # Check if AZ_DICOM_ENDPOINT_CLIENT_ID is set
    return config("AZ_DICOM_ENDPOINT_CLIENT_ID", default="") != ""


def OnChange(changeType, level, resource):  # noqa: ARG001
    """
    - If `should_export` returns `false`, the do nothing
    - Otherwise:
        - If orthanc has started then start a timer to refresh the Azure token every 30 seconds
        - If orthanc has stopped then cancel the timer
    """
    if not should_export():
        return

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


def _anonymise_dicom_instance(dataset: pydicom.Dataset) -> bytes:
    """
    Anonymise a DICOM instance.

    Skip the instance for a study if a PIXLDiscardError is raised.
    """
    try:
        study_identifiers = get_study_info(dataset)
        anonymise_and_validate_dicom(dataset, config_path=None, synchronise_pixl_db=True)
        return write_dataset_to_bytes(dataset)
    except PixlDiscardError as error:
        logger.warning("Skipping instance for study {}: {}", study_identifiers, error)
        raise


def ImportStudyFromRaw(output, uri, **request):  # noqa: ARG001
    """
    Import a study from Orthanc Raw.

    - Pull a study from Orthanc Raw based on its resource ID. Wait for the study to be stable.
    - Iterate over instances and anonymise them
    - Re-upload the study via the dicom-web api. Wait for the study to be stable.
    - Notify the PIXL export-api to send the study the to relevant endpoint
    """
    payload = json.loads(request["body"])
    study_uid = payload["StudyInstanceUID"]
    query_id = payload["QueryID"]
    retrieve_response = json.loads(
        orthanc.RestApiPost(f"/queries/{query_id}/retrieve", json.dumps({}))
    )
    logger.debug(
        "Response from retrieving study {} from Orthan Raw: {}", study_uid, retrieve_response
    )

    # Download the zipped study from Orthanc Anon
    study_resource_id = _get_study_resource_id(study_uid=study_uid)
    zipped_study_bytes = BytesIO(orthanc.RestApiGet(f"/studies/{study_resource_id}/archive"))
    logger.trace("Study data response {}", zipped_study_bytes)

    # Delete the original study now in case anything goes wrong with the anonymisation.
    # We don't want to leave the original (non-anonymised) study on Orthanc Anon
    logger.info(
        "Deleteing non-anonymised study with UID {} and resource ID {} from Orthanc Anon",
        study_uid,
        study_resource_id,
    )
    orthanc.RestApiDelete(f"/studies/{study_resource_id}")

    # Anonymise the study, re-upload to Orthanc Anon, and notify the export API to export the study
    with ZipFile(zipped_study_bytes) as zipped_study:
        anonymised_instances_bytes, anonymised_study_uid = _anonymise_study_instances(
            zipped_study=zipped_study,
            study_uid=study_uid,
        )
    _upload_instances(anonymised_instances_bytes)
    anonymised_study_resource_id = _get_study_resource_id(study_uid=anonymised_study_uid)
    Send(study_id=anonymised_study_resource_id)


def _get_study_resource_id(study_uid: str) -> str:
    """
    Get the resource ID for an existing study based on its StudyInstanceUID.

    Returns None if there are no resources with the given StudyInstanceUID.
    Returns the resource ID if there is a single resource with the given StudyInstanceUID.
    Returns None if there are multiple resources with the given StudyInstanceUID and deletes
    the studies.
    """
    data = json.dumps(
        {
            "Level": "Study",
            "Query": {
                "StudyInstanceUID": study_uid,
            },
        }
    )
    study_resource_ids = json.loads(orthanc.RestApiPost("/tools/find", data))
    if not study_resource_ids:
        message = f"No study found with StudyInstanceUID {study_uid}"
        raise ValueError(message)
    if len(study_resource_ids) > 1:
        message = f"Multiple studies found with StudyInstanceUID {study_uid}"
        raise ValueError(message)

    return study_resource_ids[0]


def _anonymise_study_instances(zipped_study: ZipFile, study_uid: str) -> tuple[list[bytes], str]:
    """
    Iterate over all instances and anonymise them.

    Return a list of the bytes of anonymised instances, and the anonymised StudyInstanceUID.
    """
    anonymised_instances_bytes = []
    logger.debug("Zipped study infolist: {}", zipped_study.infolist())
    for file_info in zipped_study.infolist():
        with zipped_study.open(file_info) as file:
            logger.debug("Reading file {}", file)
            try:
                dataset = dcmread(file)
            except pydicom.errors.InvalidDicomError:
                logger.warning("Failed to read file {}.", file)
                raise

            try:
                logger.debug("Anonymising file: {}", file)
                anonymised_instances_bytes.append(_anonymise_dicom_instance(dataset))
            except PixlDiscardError:
                pass
            except Exception:
                logger.warning("Failed to anonymize file: {}", file)
                raise
            else:
                anonymised_study_uid = dataset[0x0020, 0x000D].value

    if not anonymised_instances_bytes:
        message = "All instances have been discarded for study {}", study_uid
        raise ValueError(message)

    return anonymised_instances_bytes, anonymised_study_uid


def _upload_instances(instances_bytes: list[bytes]) -> None:
    """Upload instances to Orthanc"""
    files = []
    for index, dicom_bytes in enumerate(instances_bytes):
        files.append(("file", (f"instance{index}.dcm", dicom_bytes, "application/dicom")))

    # Using requests as doing:
    # `upload_response = orthanc.RestApiPost(f"/instances", anonymised_files)`
    # gives an error BadArgumentType error (orthanc.RestApiPost seems to only accept json)
    upload_response = requests.post(
        url=f"{ORTHANC_URL}/instances",
        auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
        files=files,
        timeout=config("PIXL_DICOM_TRANSFER_TIMEOUT", default=180, cast=int),
    )
    upload_response.raise_for_status()


orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterRestCallback("/heart-beat", OnHeartBeat)
orthanc.RegisterRestCallback("/import-from-raw", ImportStudyFromRaw)
