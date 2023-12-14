import asyncio

import fastapi
from starlette.responses import PlainTextResponse

app = fastapi.FastAPI()


@app.get("/heart-beat", summary="Health Check")
async def heart_beat() -> str:
    return "OK"


@app.post("/redact")
async def redact(request: fastapi.Request) -> PlainTextResponse:
    await asyncio.sleep(2)
    body = await request.body()
    return PlainTextResponse(body.decode("utf-8"))
