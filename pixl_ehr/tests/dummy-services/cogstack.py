import asyncio

import fastapi
from pydantic import BaseModel

app = fastapi.FastAPI()


class Request(BaseModel):
    """Stores the request as a string"""

    query: str


@app.get("/heart-beat", summary="Health Check")
async def heart_beat() -> str:
    return "OK"


@app.post("/redact")
async def redact(request: fastapi.Request) -> str:
    await asyncio.sleep(2)
    return await request.body()
