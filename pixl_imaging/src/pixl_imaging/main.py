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
"""pixl_imaging module queries the VNA to check if a dataset exists"""

from __future__ import annotations

import importlib.metadata
import logging

from core.patient_queue.subscriber import PixlConsumer
from core.rest_api.router import router, state
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from ._processing import process_message

QUEUE_NAME = "imaging"

app = FastAPI(
    title="imaging-api",
    description="Imaging extraction service",
    version=importlib.metadata.version("pixl_imaging"),
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
    consumer = PixlConsumer(
        token_bucket=state.token_bucket, queue_name=QUEUE_NAME, callback=process_message
    )
    await run_in_threadpool(consumer.run)
