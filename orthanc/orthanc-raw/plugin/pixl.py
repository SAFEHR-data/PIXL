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
"""
Facilitates routing of stable studies from orthanc-raw to orthanc-anon

This module provides:
-OnHeartBeat: extends the REST API
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from core.logging import configure_logging
from core.tracing import configure_tracing
from decouple import config
from loguru import logger
from opentelemetry import trace
from pixl_dcmd.tagrecording import record_dicom_headers

import orthanc

if TYPE_CHECKING:
    from typing import Any

# Set up logging as main entry point
logging_level = config("LOG_LEVEL")
if not logging_level:
    logging_level = "INFO"
configure_logging(level=logging_level)

# Set up tracing to correlate traces and logs
configure_tracing()
tracer = trace.get_tracer("pixl.orthanc_raw")

logger.warning("Running logging at level {}", logging_level)


def OnHeartBeat(output, uri, **request):  # noqa: ARG001
    """Extends the REST API by registering a new route in the REST API"""
    orthanc.LogWarning("OK")
    output.AnswerBuffer("OK\n", "text/plain")


def ReceivedInstanceCallback(receivedDicom: bytes, origin: str) -> Any:  # noqa: ARG001
    """Optionally record headers from the received DICOM instance."""
    if should_record_headers():
        with tracer.start_as_current_span(name="record_dicom_headers"):
            record_dicom_headers(receivedDicom)
    return orthanc.ReceivedInstanceAction.KEEP_AS_IS, None


def should_record_headers() -> bool:
    """
    Checks whether ORTHANC_RAW_RECORD_HEADERS environment variable is
    set to true or false
    """
    return os.environ.get("ORTHANC_RAW_RECORD_HEADERS", "false").lower() == "true"


orthanc.RegisterReceivedInstanceCallback(ReceivedInstanceCallback)
orthanc.RegisterRestCallback("/heart-beat", OnHeartBeat)
