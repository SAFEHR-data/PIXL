#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
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
