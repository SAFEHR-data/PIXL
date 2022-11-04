import logging
import asyncio

import aio_pika
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from ._version import __version__

logger = logging.getLogger(__name__)
QUEUE_NAME = "ehr"

app = FastAPI(
    title="ehr-api",
    description=f"EHR extraction service",
    version=__version__,
    default_response_class=JSONResponse,
)


class AppState(BaseModel):
    refresh_rate: int = 0


state = AppState()


async def _event_loop() -> None:

    connection = await aio_pika.connect(
        "amqp://guest:guest@queue:5672/"
    )

    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(QUEUE_NAME)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                # Any exceptions put the message back onto the queue
                try:
                    print(message.body)
                    print("r=", state.refresh_rate)
                    await message.ack()
                except Exception: # noqa
                    await message.reject(requeue=True)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(_event_loop())


@app.get("/heart-beat", summary="Health Check")
async def heart_beat() -> str:
    return "OK"


class TokenRefreshUpdate(BaseModel):
    rate: int


@app.post(
    "/token-bucket-refresh-rate",
    summary="Update the refresh rate in items per second"
)
async def update_tb_refresh_rate(item: TokenRefreshUpdate):

    if item.rate < 0:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=f"Refresh rate mush be a positive integer",
        )

    state.refresh_rate = int(item.rate)
    return "Successfully updated the refresh rate"
