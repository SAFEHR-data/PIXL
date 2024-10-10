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
from zipfile import ZipFile
from time import sleep
from typing import TYPE_CHECKING, cast, Optional

import requests
from core.exceptions import PixlDiscardError
from decouple import config
from loguru import logger
from pydicom import dcmread
import pydicom

import orthanc
from pixl_dcmd._dicom_helpers import get_study_info
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
    """Anonymise a DICOM instance.

    Discard the study if a PIXLDiscardError is raised.
    """
    try:
        study_identifiers = get_study_info(dataset)
        anonymise_and_validate_dicom(dataset, config_path=None, synchronise_pixl_db=True)
        return write_dataset_to_bytes(dataset)
    except PixlDiscardError as error:
        logger.warning("Skipping instance for study {}: {}", study_identifiers, error)
        raise error
    

def ImportStudyFromRaw(output, uri, **request):
    """
    Import a study from Orthanc Raw.

    - Pull a study from Orthanc Raw based on its resource ID. Wait for the study to be stable.
    - Iterate over instances and anonymise them
    - Re-upload the study via the dicom-web api. Wait for the study to be stable.
    - Notify the PIXL export-api to send the study the to relevant endpoint
    """
    payload = json.loads(request["body"])
    study_uid = payload["StudyInstanceUID"]
    data = json.dumps({
        "Level": "Study",
        "Query": {
            "StudyInstanceUID": study_uid,
        },
    })

    orthanc.LogInfo(f"Importing study from raw: {payload}")
    logger.info("Importing study from raw: {}", payload)

    # TODO: do this query in the imaging api and pass in the query id so we can retrieve it here
    orthanc.LogInfo(f"Querying remote modality with query: {data}")
    query_response = json.loads(orthanc.RestApiPost("/modalities/PIXL-Raw/query", json.dumps(data)))
    logger.info("Query response {}", query_response)
    query_id = query_response["ID"]
    query_answers = json.loads(orthanc.RestApiGet(f"/queries/{query_id}/answers"))
    logger.info(f"query answers {query_answers}, {type(query_answers)}")
    if not query_answers:
        orthanc.LogWarning(f"No study from in modality with StudyInstanceUID: {study_uid}.")
    elif len(query_answers) > 1:
        orthanc.LogWarning(
            f"{len(query_answers)} studies foundin Orthanc Raw with StudyInstanceUID: {study_uid}. {query_answers}"
        )

    retrieve_response = json.loads(orthanc.RestApiPost(f"/queries/{query_id}/retrieve", json.dumps({})))
    orthanc.LogInfo(f"Response from retrieving study {study_uid} from Orthan Raw: {retrieve_response}")

    # Download the zipped study
    study_resource_id = _get_existing_study(study_uid=study_uid)
    if study_resource_id is None:
        return
    zipped_study = BytesIO(orthanc.RestApiGet(f"/studies/{study_resource_id}/archive"))
    logger.info("Study data response {}", zipped_study)

    # Anonymise the instances and delete the non-anonymised study. Return early if anonymisation fails.
    # It's important that as much code in this handler as possible is inside this "try" block.
    # This ensures we discard the image if anything goes wrong in the anonymisation process.
    # If the handler raises an exception the pre-anon image will be kept.
    try:
        anonymised_instances_bytes = _anonymise_study_instances(zipped_study)
    except Exception as e:
        return
    finally:
        orthanc.LogInfo(f"Deleteing non-anonymised study with UID {study_uid} and resource ID {study_resource_id} from Orthanc Anon")
        orthanc.RestApiDelete(f"/studies/{study_resource_id}")

    orthanc.LogInfo(f"Sending anonymised study to Orthanc Anon for study with original UID {study_uid}")
    _upload_instances(anonymised_instances_bytes)

    # TODO: get anonymised StudyInstanceUID, use this to get the anonymised study resource ID, then send the study for export
    # Send(anonymised_resource_id)


def _get_existing_study(study_uid: str) -> Optional[str]:
    """Get the resource ID for an existing study based on its StudyInstanceUID.

    Returns the resource ID if there is a single resource with the given StudyInstanceUID.
    Otherwise logs a warning and returns `None`.
    """
    data = json.dumps({
        "Level": "Study",
        "Query": {
            "StudyInstanceUID": study_uid,
        },
    })
    study_resource_ids = json.loads(orthanc.RestApiPost("/tools/find", data))
    if not study_resource_ids:
        orthanc.LogWarning(f"No study found with StudyInstanceUID {study_uid}")
        return
    elif len(study_resource_ids) > 1:
        orthanc.LogWarning(f"{len(study_resource_ids)} found with StudyInstanceUID {study_uid}")
        return

    return study_resource_ids[0]


def _anonymise_study_instances(zipped_study: BytesIO) -> list[bytes]:
    """Iterate over all instances and anonymise them"""

    anonymised_instances_bytes = []
    with ZipFile(zipped_study) as z:
        logger.info("Info list: {}", z.infolist())
        for file_info in z.infolist():
            with z.open(file_info) as file:
                logger.info("Reading file {}", file)
                try:
                    dataset = dcmread(file)
                except pydicom.errors.InvalidDicomError as e:
                    logger.error("Failed to read file {}. Error: {}", file, str(e))
                    raise e

                try:
                    logger.info("Anonymising file: {}", file)
                    anonymised_instance_bytes = _anonymise_dicom_instance(dataset=dataset)
                except PixlDiscardError:
                    pass
                except Exception:
                    orthanc.LogError(f"Failed to anonymize file {file} due to\n" + traceback.format_exc())
                    raise e
                else:
                    anonymised_instances_bytes.append(anonymised_instance_bytes)

    return anonymised_instances_bytes


def _upload_instances(instances_bytes):
    """Upload instances to Orthanc"""
    files = []
    for index, dicom_bytes in enumerate(instances_bytes):
        files.append(('file', (f"instance{index}.dcm", dicom_bytes, 'application/dicom')))

    # Using requests as doing:
    # `upload_response = orthanc.RestApiPost(f"/instances", anonymised_files)`
    # gives an error BadArgumentType error (orthanc.RestApiPost seems to only accept json)
    upload_response = requests.post(
            f"{ORTHANC_URL}/instances",
            auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
            files=files,
        )
    upload_response.raise_for_status()


orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterRestCallback("/heart-beat", OnHeartBeat)
orthanc.RegisterRestCallback("/import-from-raw", ImportStudyFromRaw)
