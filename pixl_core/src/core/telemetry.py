#  Copyright (c) University College London Hospitals NHS Foundation Trust
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
"""Configure OpenTelemetry for PIXL services."""

from __future__ import annotations

import atexit
import os
import sys

from decouple import config
from loguru import logger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from core.logging import OTelSink

__all__ = [
    "configure_logging",
    "configure_tracing",
    "telemetry_is_enabled",
]


def telemetry_is_enabled() -> bool:
    """
    Check whether telemetry should be enabled.

    It should be disabled if OTEL_SDK_DISABLED is true or if OTEL_EXPORTER_OTLP_ENDPOINT is not set.
    """
    disabled = config("OTEL_SDK_DISABLED", cast=bool)
    if disabled:
        logger.debug("OTEL_SDK_DISABLED is set, skipping OTel configuration")
        return False

    endpoint = config("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT is not set. Telemetry will not be sent to the collector."
        )
        # Disable the SDK to avoid errors from the OTel SDK
        os.environ["OTEL_SDK_DISABLED"] = "true"
        return False

    return True


def configure_logging(level: str) -> None:
    """
    Configure loguru for a PIXL service.

    Always logs to stderr, which will be viewable in the Docker logs. When
    OTEL_SDK_DISABLED is false and OTEL_EXPORTER_OTLP_ENDPOINT is set, also
    sends logs to the OTel collector.
    """
    logger.remove()
    logger.add(sys.stderr, level=level.upper())

    if not telemetry_is_enabled():
        return

    sink = OTelSink()
    logger.add(sink, level=level.upper())


def configure_tracing() -> None:
    """
    Set up an OTLP span exporter when OTEL_SDK_DISABLED is false
    and OTEL_EXPORTER_OTLP_ENDPOINT is set in the environment.
    """
    if not telemetry_is_enabled():
        return

    exporter = OTLPSpanExporter()
    processor = BatchSpanProcessor(exporter)
    provider = TracerProvider(resource=Resource.create())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    atexit.register(provider.shutdown)
