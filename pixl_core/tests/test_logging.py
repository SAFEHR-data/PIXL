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
"""Tests for exporting loguru logs to an OpenTelemetry collector."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from loguru import logger
from opentelemetry._logs import SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    InMemoryLogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.resources import Resource

from core.logging import OTelSink, configure_logging

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def exporter() -> InMemoryLogRecordExporter:
    """In-memory exporter capturing the OTel log records the sink emits."""
    return InMemoryLogRecordExporter()


@pytest.fixture
def otel_logger(
    exporter: InMemoryLogRecordExporter,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None]:
    """Configure an OTelSink using the in-memory exporter."""
    provider = LoggerProvider(resource=Resource.create({"service.name": "test"}))
    provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
    monkeypatch.setattr(OTelSink, "_build_provider", lambda _: provider)

    # Set catch=False so loguru doesn't swallow exceptions raised in the sink
    handler_id = logger.add(OTelSink(), level="TRACE", catch=False)
    yield
    logger.remove(handler_id)


def test_configure_logging_creates_otel_sink() -> None:
    """Test that configure_logging adds the OTel sink when the endpoint is set."""
    configure_logging(level="INFO")
    assert len(logger._core.handlers) == 2  # stderr and OTel sink


@pytest.mark.usefixtures("otel_logger")
def test_otel_sink_logs_messages(exporter: InMemoryLogRecordExporter) -> None:
    """Test that loguru records are sent to the OTel exporter."""
    logger.info("A test message")

    record = exporter.get_finished_logs()[0].log_record
    assert record.body == "A test message"


@pytest.mark.usefixtures("otel_logger")
def test_severity_mapping(exporter: InMemoryLogRecordExporter) -> None:
    """Test loguru levels map correctly to the configured OTel severity name and number."""
    logger.trace("Trace message.")
    logger.info("This is informative.")
    logger.success("Well done!")

    records = [data.log_record for data in exporter.get_finished_logs()]
    assert [(r.severity_text, r.severity_number) for r in records] == [
        ("TRACE", SeverityNumber.TRACE),
        ("INFO", SeverityNumber.INFO),
        ("SUCCESS", SeverityNumber.INFO2),
    ]


@pytest.mark.usefixtures("otel_logger")
def test_exception_is_captured(exporter: InMemoryLogRecordExporter) -> None:
    """
    Test that exception type, message and attribute are recorded when calling
    logger.exception.
    """

    def _bad_function() -> None:
        msg = "big error"
        raise ValueError(msg)

    try:
        _bad_function()
    except ValueError:
        logger.exception("failed")

    record = exporter.get_finished_logs()[0].log_record
    attributes = dict(record.attributes)

    assert record.severity_text == "ERROR"
    assert attributes["exception.type"] == "ValueError"
    assert attributes["exception.message"] == "big error"
    assert "big error" in attributes["exception.stacktrace"]
