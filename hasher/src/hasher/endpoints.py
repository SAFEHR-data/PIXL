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
"""Sets up endpoints for the hasher-api"""

from __future__ import annotations

from fastapi import APIRouter
from starlette.responses import Response

from hasher.hashing import Hasher

router = APIRouter()
hasher = Hasher()


@router.get("/heart-beat", summary="Health Check")
async def heart_beat() -> str:
    return "OK"


@router.get(
    "/hash",
    summary="Produce secure hash with optional max output length (2 <= length <= 64)",
)
async def hash(message: str, length: int = 64) -> Response:  # noqa: A001
    output = hasher.generate_hash(message, length)
    return Response(content=output, media_type="application/text")


@router.get("/salt", summary="Generate a salt of length (2 <= length <= 16)")
async def salt(project_name: str, max_length: int = 16) -> Response:
    output = hasher.fetch_salt(project_name, max_length)
    return Response(content=output, media_type="application/text")


@router.get(
    "/hash-accession-number",
    summary="Produce secure hash appropriate for an accession number",
)
async def hash_accession_number(message: str) -> Response:
    truncated_output = hasher.generate_hash(message, 64)[:16]
    return Response(content=truncated_output, media_type="application/text")


@router.get(
    "/hash-mrn",
    summary="Produce secure hash appropriate for an patient identifier (MRN)",
)
async def hash_mrn(message: str) -> Response:
    return Response(content=hasher.generate_hash(message, 64), media_type="application/text")
