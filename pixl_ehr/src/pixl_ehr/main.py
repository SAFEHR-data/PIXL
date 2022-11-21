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
from typing import Callable

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pixl_ehr._processing import process_message
from pydantic import BaseModel

from token_buffer import TokenBucket
from patient_queue.subscriber import PixlConsumer
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


async def _queue_loop() -> None:
    # TODO: settings would probably be best in separate env file as done elsewhere
    consumer = PixlConsumer("ehr", 5672, "guest", "guest")
    consumer.run(state.token_bucket)


@app.on_event("startup")
async def startup_event() -> None:

    asyncio.create_task(_queue_loop())


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

    state.token_bucket = TokenBucket(rate=int(item.rate), capacity=5)
    return "Successfully updated the refresh rate"


@app.get(
    "/token-bucket-refresh-rate", summary="Get the refresh rate in items per second"
)
async def get_tb_refresh_rate() -> BaseModel:
    return TokenRefreshUpdate(rate=state.token_bucket.rate)
