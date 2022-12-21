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

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from patient_queue.subscriber import PixlConsumer
from pixl_pacs._processing import process_message
from pydantic import BaseModel

from token_buffer import TokenBucket

from ._version import __version__

QUEUE_NAME = "pacs"

app = FastAPI(
    title="pacs-api",
    description="PACS extraction service",
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
    rate: float


@app.post(
    "/token-bucket-refresh-rate", summary="Update the refresh rate in items per second"
)
async def update_tb_refresh_rate(item: TokenRefreshUpdate) -> str:

    if not isinstance(item.rate, float) or item.rate < 0:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=f"Refresh rate mush be a positive integer. Had {item.rate}",
        )

    state.token_bucket.rate = float(item.rate)
    return "Successfully updated the refresh rate"


@app.get(
    "/token-bucket-refresh-rate", summary="Get the refresh rate in items per second"
)
async def get_tb_refresh_rate() -> BaseModel:
    return TokenRefreshUpdate(rate=state.token_bucket.rate)
