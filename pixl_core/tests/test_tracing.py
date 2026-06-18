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
"""Tests for OpenTelemetry tracing setup and log/trace correlation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from loguru import logger
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

if TYPE_CHECKING:
    from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter
    from opentelemetry.trace import Tracer


@pytest.fixture
def otel_tracer() -> Tracer:
    """A tracer backed by the in-memory span exporter (local, not the global provider)."""
    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    provider = TracerProvider()
    provider.add_span_processor(processor)
    return provider.get_tracer("test")


@pytest.mark.usefixtures("otel_logger")
def test_log_outside_span_has_no_trace_context(log_exporter: InMemoryLogRecordExporter) -> None:
    """Test logs emitted with no active span have no trace context."""
    logger.info("no span here")

    record = log_exporter.get_finished_logs()[0].log_record
    assert not record.trace_id
    assert not record.span_id


@pytest.mark.usefixtures("otel_logger")
def test_log_is_correlated_with_active_span(
    otel_tracer: Tracer,
    log_exporter: InMemoryLogRecordExporter,
) -> None:
    """Test logs emitted within a span carry that span's trace_id and span_id."""
    with otel_tracer.start_as_current_span("test_span") as span:
        logger.info("inside the span")
    span_context = span.get_span_context()

    record = log_exporter.get_finished_logs()[0].log_record
    assert record.trace_id == span_context.trace_id
    assert record.span_id == span_context.span_id
