import asyncio

import aio_pika
import token_bucket as tb

from fastapi.logger import logger
from dataclasses import dataclass
from typing import Callable
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pixl_ehr._processing import process_message
from ._version import __version__

QUEUE_NAME = "ehr"

app = FastAPI(
    title="ehr-api",
    description="EHR extraction service",
    version=__version__,
    default_response_class=JSONResponse,
)


class PixlTokenBucket(tb.Limiter):
    # TODO: https://github.com/UCLH-DIF/PIXL/issues/49

    def __init__(self, rate: int, capacity: int, storage: tb.StorageBase):

        self._zero_rate = False

        if rate == 0:
            # tb.Limiter cannot deal with zero rates, so keep track...
            rate = 1
            self._zero_rate = True

        super().__init__(rate=rate, capacity=capacity, storage=storage)

    @property
    def has_token(self) -> bool:
        return not self._zero_rate and bool(self.consume("pixl"))


@dataclass
class AppState:
    token_bucket = PixlTokenBucket(rate=0, capacity=5, storage=tb.MemoryStorage())


state = AppState()


async def _queue_loop(callback: Callable = process_message) -> None:

    # TODO: replace with RabbitMQ connection username+password+port
    connection = await aio_pika.connect("amqp://guest:guest@queue:5672/")

    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(QUEUE_NAME)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:

                try:
                    if state.token_bucket.has_token:
                        callback(message.body)
                        await message.ack()
                    else:
                        await message.reject(requeue=True)
                except Exception as e:  # noqa
                    logger.error(
                        f"Failed to process {message.body.decode()} due to\n{e}\n"
                        f"Not re-queuing message"
                    )
                    await message.reject(requeue=False)


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

    state.token_bucket = PixlTokenBucket(
        rate=int(item.rate), capacity=5, storage=tb.MemoryStorage()
    )
    return "Successfully updated the refresh rate"
