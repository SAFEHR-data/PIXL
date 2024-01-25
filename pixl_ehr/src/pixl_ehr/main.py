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
import logging
from datetime import (
    datetime,  # noqa: TCH003, always import datetime otherwise pydantic throws error
)
from pathlib import Path
from typing import Optional

from azure.identity import EnvironmentCredential
from azure.storage.blob import BlobServiceClient
from core.exports import ParquetExport
from core.patient_queue import PixlConsumer
<<<<<<< HEAD
from core.rest_api.router import router, state
=======
from core.router import router, state
from core.upload import upload_radiology_reports
>>>>>>> 76c5655 (pair prog switchover)
from decouple import config
from fastapi import FastAPI
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
    async with PixlConsumer(QUEUE_NAME, token_bucket=state.token_bucket) as consumer:
        task = asyncio.create_task(consumer.run(callback=process_message))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)


# Export root dir from inside the EHR container.
# For the view from outside, see pixl_cli/_io.py: HOST_EXPORT_ROOT_DIR
EHR_EXPORT_ROOT_DIR = Path("/run/exports")


class ExportRadiologyData(BaseModel):
    """there may be entries from multiple extracts in the PIXL database, so filtering is needed"""

    project_name: str
    extract_datetime: datetime
    output_dir: Optional[Path] = EHR_EXPORT_ROOT_DIR


@app.post(
    "/export-radiology-as-parquet",
    summary="Copy all matching radiology reports in the PIXL DB to a parquet file",
)
def export_radiology_as_parquet(export_params: ExportRadiologyData) -> None:
    """
    Batch export of all matching radiology reports in PIXL DB to a parquet file.
    NOTE: we can't check that all reports in the queue have been processed, so
    we are relying on the user waiting until processing has finished before running this.
    """
    pe = ParquetExport(
        export_params.project_name, export_params.extract_datetime, export_params.output_dir
    )
    anon_data = PIXLDatabase().get_radiology_reports(
        pe.project_slug, export_params.extract_datetime
    )
    pe.export_radiology(anon_data)

@app.post(
"/send-parquet-files-via-FTPS",
summary="Copy/send all ParquetExports via FTPS",
)
def SendViaFTPS(project_name: str, extract_datetime: datetime) -> None:
    """
    fdsfasfd af dfdsfds
    sdff
    """
    pe = ParquetExport(project_name, extract_datetime)
    upload_radiology_reports(pe)


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

    with Path(file=csv_filename, mode="rb").open() as data:
        blob_client.upload_blob(data)

    logger.info("Uploaded successfully!")


def _storage_account_url() -> str:
    """Provides the storage account url"""
    return f"https://{config('AZ_STORAGE_ACCOUNT_NAME')}.blob.core.windows.net"
