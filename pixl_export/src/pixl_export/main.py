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
"""pixl_export module is an EHR extraction service app"""

from __future__ import annotations

import importlib.metadata
import logging
from datetime import (
    datetime,  # noqa: TCH003, always import datetime otherwise pydantic throws error
)
from pathlib import Path

from core.exports import ParquetExport
from core.project_config import load_project_config
from core.rest_api.router import router
from core.uploader import get_uploader
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ._orthanc import get_study_zip_archive, get_tags_by_study

app = FastAPI(
    title="export-api",
    description="Export service",
    version=importlib.metadata.version("pixl_export"),
    default_response_class=JSONResponse,
)
app.include_router(router)

logger = logging.getLogger("uvicorn")

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
    hashed_image_id, project_slug = get_tags_by_study(study_id)
    project_config = load_project_config(project_slug)
    destination = project_config.destination.dicom

    uploader = get_uploader(project_slug, destination, project_config.project.azure_kv_alias)
    msg = f"Sending {study_id} via '{destination}'"
    logger.debug(msg)
    zip_content = get_study_zip_archive(study_id)
    uploader.upload_dicom_image(zip_content, hashed_image_id, project_slug)