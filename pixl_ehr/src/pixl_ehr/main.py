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
import asyncio
from dataclasses import dataclass
import logging

from azure.identity import EnvironmentCredential
from azure.storage.blob import BlobServiceClient
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from patient_queue.subscriber import PixlConsumer
from pixl_ehr._databases import PIXLDatabase
from pixl_ehr._processing import process_message
from pixl_ehr.utils import env_var
from pydantic import BaseModel

from token_buffer import TokenBucket

from ._version import __version__

QUEUE_NAME = "ehr"

app = FastAPI(
    title="ehr-api",
    description="EHR extraction service",
    version=__version__,
    default_response_class=JSONResponse,
)

logger = logging.getLogger("uvicorn")


@dataclass
class AppState:
    token_bucket = TokenBucket(rate=0, capacity=5)


state = AppState()


@app.on_event("startup")
async def startup_event() -> None:
    async with PixlConsumer(QUEUE_NAME, token_bucket=state.token_bucket) as consumer:
        asyncio.create_task(consumer.run(callback=process_message))


@app.get("/heart-beat", summary="Health Check")
async def heart_beat() -> str:
    return "OK"


class TokenRefreshUpdate(BaseModel):
    rate: int


@app.post(
    "/token-bucket-refresh-rate", summary="Update the refresh rate in items per second"
)
async def update_tb_refresh_rate(item: TokenRefreshUpdate) -> str:

    if not isinstance(item.rate, int) or item.rate < 0:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=f"Refresh rate mush be a positive integer. Had {item.rate}",
        )

    state.token_bucket.rate = int(item.rate)
    return "Successfully updated the refresh rate"


@app.get(
    "/token-bucket-refresh-rate", summary="Get the refresh rate in items per second"
)
async def get_tb_refresh_rate() -> BaseModel:
    return TokenRefreshUpdate(rate=state.token_bucket.rate)


@app.get(
    "/az-copy-current",
    summary="Copy the current state of the PIXL anon EHR schema to azure",
)
async def az_copy_current(csv_filename: str = "tmp_extract.csv") -> None:
    logger.info("Copying current state of anon schema to azure")

    PIXLDatabase().to_csv(
        schema_name="emap_data", table_name="ehr_anon", filename=csv_filename
    )
    logger.debug(f"Saved temporary .csv ({csv_filename})")

    blob_service_client = BlobServiceClient(
        account_url=_storage_account_url(),
        credential=EnvironmentCredential(),
    )
    logger.debug(f"Have blob client for {env_var('AZ_STORAGE_ACCOUNT_NAME')}")

    # Create a blob client using the local file name as the name for the blob
    blob_client = blob_service_client.get_blob_client(
        container=env_var("AZ_STORAGE_CONTAINER_NAME"), blob=csv_filename
    )

    logger.info(
        f"Uploading to Azure Storage as blob: "
        f"{env_var('AZ_STORAGE_CONTAINER_NAME')}/{csv_filename}"
    )

    with open(file=csv_filename, mode="rb") as data:
        blob_client.upload_blob(data)

    logger.info("Uploaded successfully!")


def _storage_account_url() -> str:
    return f"https://{env_var('AZ_STORAGE_ACCOUNT_NAME')}.blob.core.windows.net"
