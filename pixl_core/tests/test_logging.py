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

from core.logging import OTelSink, configure_logging

if TYPE_CHECKING:
    from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter


def test_build_provider_reuses_existing_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that OTelSink reuses a LoggerProvider already set by opentelemetry-instrument."""
    existing = LoggerProvider()
    monkeypatch.setattr("core.logging.get_logger_provider", lambda: existing)
    sink = OTelSink()
    assert sink.provider is existing


def test_configure_logging_skips_otel_when_sdk_disabled() -> None:
    """Test that configure_logging only adds stderr when OTEL_SDK_DISABLED is true."""
    configure_logging(level="INFO")
    assert len(logger._core.handlers) == 1  # stderr only
    logger.remove()


def test_configure_logging_creates_otel_sink(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that configure_logging adds the OTel sink when telemetry is enabled."""
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    configure_logging(level="INFO")
    assert len(logger._core.handlers) == 2  # stderr and OTel sink
    logger.remove()


@pytest.mark.usefixtures("otel_logger")
def test_otel_sink_logs_messages(log_exporter: InMemoryLogRecordExporter) -> None:
    """Test that loguru records are sent to the OTel exporter."""
    logger.info("A test message")

    record = log_exporter.get_finished_logs()[0].log_record
    assert record.body == "A test message"


@pytest.mark.usefixtures("otel_logger")
def test_bound_fields_become_attributes(log_exporter: InMemoryLogRecordExporter) -> None:
    """Test that bound fields are exported as top-level OTel log attributes."""
    logger.bind(
        project_name="test-project",
        study_uid="1.2.3",
    ).info("Processing study.")

    record = log_exporter.get_finished_logs()[0].log_record
    attributes = dict(record.attributes)

    assert record.body == "Processing study."
    assert attributes["study_uid"] == "1.2.3"
    assert attributes["project_name"] == "test-project"
    assert attributes["code.function"] == "test_bound_fields_become_attributes"
    assert attributes["code.lineno"] > 0
    assert str(attributes["code.filepath"]).endswith("test_logging.py")


@pytest.mark.usefixtures("otel_logger")
def test_severity_mapping(log_exporter: InMemoryLogRecordExporter) -> None:
    """Test loguru levels map correctly to the configured OTel severity name and number."""
    logger.trace("Trace message.")
    logger.info("This is informative.")
    logger.success("Well done!")

    records = [data.log_record for data in log_exporter.get_finished_logs()]
    assert [(r.severity_text, r.severity_number) for r in records] == [
        ("TRACE", SeverityNumber.TRACE),
        ("INFO", SeverityNumber.INFO),
        ("SUCCESS", SeverityNumber.INFO2),
    ]


@pytest.mark.usefixtures("otel_logger")
def test_exception_is_captured(log_exporter: InMemoryLogRecordExporter) -> None:
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

    record = log_exporter.get_finished_logs()[0].log_record
    attributes = dict(record.attributes)

    assert record.severity_text == "ERROR"
    assert attributes["exception.type"] == "ValueError"
    assert attributes["exception.message"] == "big error"
    assert "big error" in attributes["exception.stacktrace"]
