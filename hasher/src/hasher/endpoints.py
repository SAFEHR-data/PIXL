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

from fastapi import APIRouter
from starlette.responses import Response

from hasher.hashing import generate_hash, generate_salt

router = APIRouter()


@router.get("/heart-beat", summary="Health Check")
async def heart_beat() -> str:
    return "OK"


@router.get(
    "/hash",
    summary="Produce secure hash with optional max output length (2 <= length <= 64)",
)
async def hash(message: str, length: int = 64) -> Response:
    output = generate_hash(message, length)
    return Response(content=output, media_type="application/text")


@router.get("/salt", summary="Generate a salt of length (2 <= length <= 16)")
async def salt(length: int = 16) -> Response:
    output = generate_salt(length)
    return Response(content=output, media_type="application/text")
