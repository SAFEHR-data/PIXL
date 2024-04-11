#  Copyright (c) University College London Hospitals NHS Foundation Trust
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
"""pixl_ehr module is an EHR extraction service app"""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import logging
import threading
from datetime import (
    datetime,  # noqa: TCH003, always import datetime otherwise pydantic throws error
)
from io import BytesIO
from pathlib import Path
from time import sleep
from typing import cast

import requests
from azure.identity import EnvironmentCredential
from azure.storage.blob import BlobServiceClient
from core.exports import ParquetExport
from core.patient_queue import PixlConsumer
from core.project_config import load_project_config
from core.rest_api.router import router, state
from core.uploader import get_uploader
from decouple import config
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ._databases import PIXLDatabase
from ._processing import process_message

QUEUE_NAME = "ehr"

app = FastAPI(
    title="ehr-api",
    description="EHR extraction service",
    version=importlib.metadata.version("pixl_ehr"),
    default_response_class=JSONResponse,
)
app.include_router(router)

logger = logging.getLogger("uvicorn")


@app.on_event("startup")
async def startup_event() -> None:
    """
    task create: the coroutine submitted to run "in the background",
    i.e. concurrently with the current task and all other tasks,
    switching between them at await points
    the task is consumer.run and the callback is _processing.process_message
    """
    background_tasks = set()
    async with PixlConsumer(
        QUEUE_NAME, token_bucket=state.token_bucket, callback=process_message
    ) as consumer:
        task = asyncio.create_task(consumer.run())
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)


# Export root dir from inside the EHR container.
# For the view from outside, see pixl_cli/_io.py: HOST_EXPORT_ROOT_DIR
EHR_EXPORT_ROOT_DIR = Path("/run/projects/exports")


class ExportPatientData(BaseModel):
    """there may be entries from multiple extracts in the PIXL database, so filtering is needed"""

    project_name: str
    extract_datetime: datetime
    output_dir: Path = EHR_EXPORT_ROOT_DIR


class StudyData(BaseModel):
    """Uniquely identify a study when talking to the API"""

    study_id: str


@app.post(
    "/export-patient-data",
    summary="Copy all matching radiology reports in the PIXL DB to a parquet file \
    and send all ParquetExports via FTPS",
)
def export_patient_data(export_params: ExportPatientData) -> None:
    """
    Batch export of all matching radiology reports in PIXL DB to a parquet file.
    NOTE: we can't check that all reports in the queue have been processed, so
    we are relying on the user waiting until processing has finished before running this.
    """
    logger.info("Exporting Patient Data for '%s'", export_params.project_name)
    export_radiology_as_parquet(export_params)

    # Upload Parquet files to the appropriate endpoint
    parquet_export = ParquetExport(
        export_params.project_name, export_params.extract_datetime, export_params.output_dir
    )

    try:
        parquet_export.upload()
    except ValueError as e:
        msg = "Destination for parquet files unavailable"
        logger.exception(msg)
        raise HTTPException(status_code=400, detail=msg) from e


ORTHANC_ANON_USERNAME = config("ORTHANC_ANON_USERNAME")
ORTHANC_ANON_PASSWORD = config("ORTHANC_ANON_PASSWORD")
ORTHANC_ANON_URL = "http://orthanc-anon:8042"


@app.post(
    "/export-dicom-from-orthanc",
    summary="Download a zipped up study from orthanc anon and upload it via the appropriate route",
)
def export_dicom_from_orthanc(study_data: StudyData) -> None:
    """
    Download zipped up study data from orthanc anon and route it appropriately.
    Intended only for orthanc-anon to call, as only it knows when its data is ready for download.
    Because we're post-anonymisation, the "PatientID" tag returned is actually
    the hashed image ID (MRN + Accession number).
    """
    study_id = study_data.study_id
    hashed_image_id, project_slug = _get_tags_by_study(study_id)
    project_config = load_project_config(project_slug)
    destination = project_config.destination.dicom

    uploader = get_uploader(project_slug, destination, project_config.project.azure_kv_alias)
    msg = f"Sending {study_id} via '{destination}'"
    logger.debug(msg)
    zip_content = _get_study_zip_archive(study_id)
    # XXX: perhaps need to use this abstraction for DICOMWEB and Azure DICOM upload?
    # How do they do it currently?
    # Be sure to call _azure_available() before doing any Azure stuff
    # (used to be done in orthanc anon plugin)
    uploader.upload_dicom_image(zip_content, hashed_image_id, project_slug)


def _get_study_zip_archive(resourceId: str) -> BytesIO:
    # Download zip archive of the DICOM resource
    query = f"{ORTHANC_ANON_URL}/studies/{resourceId}/archive"
    fail_msg = "Could not download archive of resource '%s'"
    response_study = _query(resourceId, query, fail_msg)

    # get the zip content
    logger.debug("Downloaded data for resource %s", resourceId)
    return BytesIO(response_study.content)


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

    return cast(str, response.json()["access_token"])


def _get_tags_by_study(study_id: str) -> tuple[str, str]:
    """
    Queries the Orthanc server at the study level, returning the
    PatientID and UCLHPIXLProjectName DICOM tags.
    BEWARE: post-anonymisation, the PatientID is NOT
    the patient ID, it's the pseudo-anonymised ID generated
    from the hash of the concatenated Patient ID (MRN) and Accession Number fields.
    """
    query = f"{ORTHANC_ANON_URL}/studies/{study_id}/shared-tags?simplify=true"
    fail_msg = "Could not query study for resource '%s'"

    response_study = _query(study_id, query, fail_msg)
    json_response = json.loads(response_study.content.decode())
    return json_response["PatientID"], json_response["UCLHPIXLProjectName"]


def _query(resourceId: str, query: str, fail_msg: str) -> requests.Response:
    try:
        response = requests.get(
            query, auth=(ORTHANC_ANON_USERNAME, ORTHANC_ANON_PASSWORD), timeout=10
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        logger.exception("Failed to query resource '%s', error: '%s'", resourceId, fail_msg)
        raise
    else:
        return response


def _azure_available() -> bool:
    # Check if AZ_DICOM_ENDPOINT_CLIENT_ID is set
    return bool(config("AZ_DICOM_ENDPOINT_CLIENT_ID", default="") != "")


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

    logger.warning("Refreshing Azure DICOM token")

    AZ_DICOM_TOKEN_REFRESH_SECS = int(config("AZ_DICOM_TOKEN_REFRESH_SECS"))
    AZ_DICOM_ENDPOINT_NAME = config("AZ_DICOM_ENDPOINT_NAME")
    AZ_DICOM_ENDPOINT_URL = config("AZ_DICOM_ENDPOINT_URL")
    AZ_DICOM_HTTP_TIMEOUT = int(config("HTTP_TIMEOUT"))

    try:
        access_token = AzureAccessToken()
    except Exception:
        logger.exception("Failed to get an Azure access token. Retrying in 30 seconds")
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

    url = ORTHANC_ANON_URL + "/dicom-web/servers/" + AZ_DICOM_ENDPOINT_NAME

    try:
        requests.put(
            url,
            auth=(ORTHANC_ANON_USERNAME, ORTHANC_ANON_PASSWORD),
            headers=headers,
            data=json.dumps(dicomweb_config),
            timeout=10,
        )
    except requests.exceptions.RequestException as e:
        logger.exception("Failed to update DICOMweb token")
        raise SystemExit(e)  # noqa: TRY200, B904

    logger.warning("Updated DICOMweb token")

    TIMER = threading.Timer(AZ_DICOM_TOKEN_REFRESH_SECS, AzureDICOMTokenRefresh)
    TIMER.start()
    return None


def SendViaStow(resourceId: str) -> None:
    """
    Makes a POST API call to upload the resource to a dicom-web server
    using orthanc credentials as authorisation
    """
    AZ_DICOM_ENDPOINT_NAME = config("AZ_DICOM_ENDPOINT_NAME")
    url = ORTHANC_ANON_URL + "/dicom-web/servers/" + AZ_DICOM_ENDPOINT_NAME + "/stow"
    headers = {"content-type": "application/json"}
    payload = {"Resources": [resourceId], "Synchronous": False}
    logger.debug("Payload: %s", payload)
    try:
        resp = requests.post(
            url,
            auth=(ORTHANC_ANON_USERNAME, ORTHANC_ANON_PASSWORD),
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        resp.raise_for_status()
        msg = f"Sent {resourceId} via STOW"
        logger.info(msg)
    except requests.exceptions.RequestException:
        logger.exception("Failed to send via STOW")


def export_radiology_as_parquet(export_params: ExportPatientData) -> None:
    """
    Export radiology reports as a parquet file to
    `{EHR_EXPORT_ROOT_DIR}/<project-slug>/all_extracts/radiology/radiology.parquet`.
    :param export_params: the project name, extract datetime and output directory defined as an
        ExportPatientData object.
    """
    pe = ParquetExport(
        export_params.project_name, export_params.extract_datetime, export_params.output_dir
    )

    anon_data = PIXLDatabase().get_radiology_reports(
        pe.project_slug, export_params.extract_datetime
    )
    pe.export_radiology(anon_data)


@app.get(
    "/az-copy-current",
    summary="Copy the current state of the PIXL anon EHR schema to azure",
)
async def az_copy_current(csv_filename: str = "extract.csv") -> None:
    """
    Copy the current state of the PIXL anon EHR schema to azure
    Args:
        csv_filename (str, optional): _description_. Defaults to "extract.csv".
    """
    logger.info("Copying current state of anon schema to azure")

    PIXLDatabase().to_csv(schema_name="emap_data", table_name="ehr_anon", filename=csv_filename)
    logger.debug("Saved temporary .csv (%s)", csv_filename)

    blob_service_client = BlobServiceClient(
        account_url=_storage_account_url(),
        credential=EnvironmentCredential(),
    )
    logger.debug("Have blob client for %s", config("AZ_STORAGE_ACCOUNT_NAME"))

    # Create a blob client using the local file name as the name for the blob
    blob_client = blob_service_client.get_blob_client(
        container=config("AZ_STORAGE_CONTAINER_NAME"), blob=csv_filename
    )

    logger.info(
        "Uploading to Azure Storage as blob: %s/%s",
        config("AZ_STORAGE_CONTAINER_NAME"),
        csv_filename,
    )

    with Path(file=csv_filename, mode="rb").open() as data:  # noqa: ASYNC101
        blob_client.upload_blob(data)

    logger.info("Uploaded successfully!")


def _storage_account_url() -> str:
    """Provides the storage account url"""
    return f"https://{config('AZ_STORAGE_ACCOUNT_NAME')}.blob.core.windows.net"
