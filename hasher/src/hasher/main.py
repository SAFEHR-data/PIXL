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
"""Defines the FastAPI app for the hasher"""

from __future__ import annotations

import sys

from decouple import config  # type: ignore [import-untyped]
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from hasher import __version__, icon
from hasher.endpoints import router

app = FastAPI(
    title="hasher-api",
    description=f"{icon} Secure Hashing Service ",
    version=__version__,
    debug=config("DEBUG", default=True),
    default_response_class=JSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Set up logging as main entry point
logger.remove()  # Remove all handlers added so far, including the default one.
logging_level = config("LOG_LEVEL", default="INFO")
if not logging_level:
    logging_level = "INFO"
logger.add(sys.stderr, level=logging_level)

logger.warning("Running logging at level {}", logging_level)

logger.info("Starting {} hasher-api {}...", icon, __version__)
