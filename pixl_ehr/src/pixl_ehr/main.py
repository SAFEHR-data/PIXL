import logging
import asyncio

from time import sleep
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from ._version import __version__

logger = logging.getLogger(__name__)


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
    while True:
        print(state)
        await asyncio.sleep(1)


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
