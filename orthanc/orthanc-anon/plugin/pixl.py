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
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from time import sleep
from typing import TYPE_CHECKING, cast
from zipfile import ZipFile

import pydicom
import requests
from core.exceptions import PixlDiscardError, PixlSkipInstanceError
from core.project_config.pixl_config_model import load_project_config
from decouple import config
from loguru import logger
from pydicom import dcmread

import orthanc
from pixl_dcmd.dicom_helpers import get_study_info
from pixl_dcmd.main import (
    anonymise_dicom_and_update_db,
    parse_validation_results,
    write_dataset_to_bytes,
)

if TYPE_CHECKING:
    from typing import Any

    from core.project_config.pixl_config_model import PixlConfig

    from pixl_dcmd.dicom_helpers import StudyInfo

ORTHANC_USERNAME = config("ORTHANC_USERNAME")
ORTHANC_PASSWORD = config("ORTHANC_PASSWORD")
ORTHANC_URL = "http://localhost:8042"

ORTHANC_RAW_USERNAME = config("ORTHANC_RAW_USERNAME")
ORTHANC_RAW_PASSWORD = config("ORTHANC_RAW_PASSWORD")
ORTHANC_RAW_URL = "http://orthanc-raw:8042"

EXPORT_API_URL = "http://export-api:8000"

# Set up logging as main entry point
logger.remove()  # Remove all handlers added so far, including the default one.
logging_level = config("LOG_LEVEL")
if not logging_level:
    logging_level = "INFO"
logger.add(sys.stdout, level=logging_level)

logger.warning("Running logging at level {}", logging_level)

# Set up a thread pool executor for non-blocking calls to Orthanc
max_workers = config("PIXL_MAX_MESSAGES_IN_FLIGHT", cast=int)
executor = ThreadPoolExecutor(max_workers=max_workers)

logger.info("Using {} threads for processing", max_workers)


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


def ImportStudiesFromRaw(output, uri, **request):  # noqa: ARG001
    """
    Import studies from Orthanc Raw.

    Offload to a thread pool executor to avoid blocking the Orthanc main thread.
    """
    payload = json.loads(request["body"])
    study_resource_ids = payload["ResourceIDs"]
    study_uids = payload["StudyInstanceUIDs"]
    project_name = payload["ProjectName"]

    executor.submit(_import_studies_from_raw, study_resource_ids, study_uids, project_name)

    response = json.dumps({"Message": "Ok"})
    output.AnswerBuffer(response, "application/json")


def _import_studies_from_raw(
    study_resource_ids: list[str], study_uids: list[str], project_name: str
) -> None:
    """
    Import studies from Orthanc Raw.

    Args:
        study_resource_ids: Resource IDs of the study in Orthanc Raw
        project_name: Name of the project

    - Pull studies from Orthanc Raw based on its resource ID
    - Iterate over instances and anonymise them
    - Upload the studies to orthanc-anon
    - Notify the PIXL export-api to send the studies to the relevant endpoint for the project

    """
    anonymised_study_uids = []

    for study_resource_id, study_uid in zip(study_resource_ids, study_uids, strict=False):
        logger.debug("Processing project '{}', study '{}' ", project_name, study_uid)
        anonymised_uid = _anonymise_study_and_upload(study_resource_id, project_name)
        if anonymised_uid:
            anonymised_study_uids.append(anonymised_uid)

    if not should_export():
        logger.debug("Not exporting study {} as auto-routing is disabled", anonymised_study_uids)
        return

    # ensure we only have unique resource ids by using a set
    resource_ids = {
        _get_study_resource_id(anonymised_study_uid)
        for anonymised_study_uid in anonymised_study_uids
    }

    logger.debug(
        "Notify export API to retrieve study resources. Original UID {} Anon UID: {}",
        study_resource_ids,
        resource_ids,
    )

    for resource_id in resource_ids:
        send_study(study_id=resource_id, project_name=project_name)


def _anonymise_study_and_upload(study_resource_id: str, project_name: str) -> str | None:
    zipped_study_bytes = get_study_zip_archive_from_raw(resource_id=study_resource_id)

    study_info = _get_study_info_from_first_file(zipped_study_bytes)
    logger.info("Processing project '{}', {}", project_name, study_info)

    with ZipFile(zipped_study_bytes) as zipped_study:
        try:
            anonymised_instances_bytes, anonymised_study_uid = _anonymise_study_instances(
                zipped_study=zipped_study,
                study_info=study_info,
                project_name=project_name,
            )
        except PixlDiscardError as discard:
            logger.warning(
                "Failed to anonymize project: '{}', {}: {}", project_name, study_info, discard
            )
            return None
        except Exception:  # noqa: BLE001
            logger.exception("Failed to anonymize project: '{}', {}", project_name, study_info)
            return None

    _upload_instances(anonymised_instances_bytes)
    return anonymised_study_uid


def get_study_zip_archive_from_raw(resource_id: str) -> BytesIO:
    """Download zip archive of study resource from Orthanc Raw."""
    query = f"{ORTHANC_RAW_URL}/studies/{resource_id}/archive"
    response = requests.get(
        query,
        auth=(config("ORTHANC_RAW_USERNAME"), config("ORTHANC_RAW_PASSWORD")),
        timeout=config("PIXL_DICOM_TRANSFER_TIMEOUT", default=180, cast=int),
    )
    response.raise_for_status()
    logger.debug("Downloaded data for resource {} from Orthanc Raw", resource_id)
    return BytesIO(response.content)


def _get_study_info_from_first_file(zipped_study_bytes) -> StudyInfo:
    with ZipFile(zipped_study_bytes) as zipped_study:
        file_info = zipped_study.infolist()[0]
        with zipped_study.open(file_info) as file:
            dataset = dcmread(file)
            return get_study_info(dataset)


def _anonymise_study_instances(
    zipped_study: ZipFile, study_info: StudyInfo, project_name: str
) -> tuple[list[bytes], str]:
    """
    Iterate over all instances and anonymise them.

    Skip an instance if a PixlSkipInstanceError is raised during anonymisation.

    Return a list of the bytes of anonymised instances, and the anonymised StudyInstanceUID.
    """
    config = load_project_config(project_name)
    series_to_skip = get_series_to_skip(zipped_study, config.min_instances_per_series)
    anonymised_instances_bytes = []
    skipped_instance_counts = defaultdict(int)
    dicom_validation_errors = {}

    for file_info in zipped_study.infolist():
        with zipped_study.open(file_info) as file:
            logger.debug("Reading file {}", file)
            dataset = dcmread(file)

            if dataset.SeriesInstanceUID in series_to_skip:
                logger.warning(
                    "Skipping series {} for study {} due to too few instances",
                    dataset.SeriesInstanceUID,
                    study_info,
                )
                continue

            try:
                anonymised_instance, instance_validation_errors = _anonymise_dicom_instance(
                    dataset, config
                )
            except PixlSkipInstanceError as e:
                logger.debug(
                    "Skipping instance {} for {}: {}",
                    dataset[0x0008, 0x0018].value,
                    study_info,
                    e,
                )
                skipped_instance_counts[str(e)] += 1
            else:
                anonymised_instances_bytes.append(anonymised_instance)
                anonymised_study_uid = dataset[0x0020, 0x000D].value
                dicom_validation_errors |= instance_validation_errors

    if not anonymised_instances_bytes:
        message = f"All instances have been skipped for study: {dict(skipped_instance_counts)}"
        raise PixlDiscardError(message)

    logger.debug(
        "Project '{}' {}, skipped instances: {}",
        project_name,
        study_info,
        dict(skipped_instance_counts),
    )

    if dicom_validation_errors:
        logger.warning(
            "The anonymisation introduced the following validation errors:\n{}",
            parse_validation_results(dicom_validation_errors),
        )
    logger.success("Finished anonymising project: '{}', {}", project_name, study_info)
    return anonymised_instances_bytes, anonymised_study_uid


def get_series_to_skip(zipped_study: ZipFile, min_instances: int) -> set[str]:
    """
    Determine which series to skip based on the number of instances in the series.

    If a series has fewer instances than `min_instances`, add it to a set of series to skip.

    Args:
        zipped_study: ZipFile containing the study
        min_instances: Minimum number of instances required to include a series

    """
    if min_instances <= 1:
        return set()

    series_instances = {}
    for file_info in zipped_study.infolist():
        with zipped_study.open(file_info) as file:
            logger.debug("Reading file {}", file)
            dataset = dcmread(file)
            if dataset.SeriesInstanceUID not in series_instances:
                series_instances[dataset.SeriesInstanceUID] = 1
                continue
            series_instances[dataset.SeriesInstanceUID] += 1

    return {series for series, count in series_instances.items() if count < min_instances}


def _anonymise_dicom_instance(dataset: pydicom.Dataset, config: PixlConfig) -> tuple[bytes, dict]:
    """Anonymise a DICOM instance."""
    validation_errors = anonymise_dicom_and_update_db(dataset, config=config)
    return write_dataset_to_bytes(dataset), validation_errors


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


def send_study(study_id: str, project_name: str) -> None:
    """
    Send the resource to the appropriate destination.
    Throws an exception if the image has already been exported.
    """
    msg = f"Sending {study_id}"
    logger.debug(msg)
    notify_export_api_of_readiness(study_id, project_name)


def notify_export_api_of_readiness(study_id: str, project_name: str) -> None:
    """
    Tell export-api that our data is ready and it should download it from us and upload
    as appropriate
    """
    url = EXPORT_API_URL + "/export-dicom-from-orthanc"
    payload = {"study_id": study_id, "project_name": project_name}
    timeout: float = config("HTTP_TIMEOUT", default=30, cast=float)
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()


orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterRestCallback("/heart-beat", OnHeartBeat)
orthanc.RegisterRestCallback("/import-from-raw", ImportStudiesFromRaw)
