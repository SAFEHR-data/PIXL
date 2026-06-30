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
"""
Provides a loguru sink that forwards records to an OpenTelemetry collector via OTLP.

Note, only loguru records are exported. Logs from third-party libraries are not
forwarded to the OTel collector.
"""

from __future__ import annotations

import atexit
from typing import TYPE_CHECKING

from opentelemetry._logs import SeverityNumber, get_logger_provider, set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

if TYPE_CHECKING:
    from loguru import Message

__all__ = ["OTelSink"]

# Map loguru level names to OTel severity
LOGURU_TO_OTEL: dict[str, SeverityNumber] = {
    "TRACE": SeverityNumber.TRACE,
    "DEBUG": SeverityNumber.DEBUG,
    "INFO": SeverityNumber.INFO,
    "SUCCESS": SeverityNumber.INFO2,
    "WARNING": SeverityNumber.WARN,
    "ERROR": SeverityNumber.ERROR,
    "CRITICAL": SeverityNumber.FATAL,
}


class OTelSink:
    """Send loguru records to an OTel logs exporter via OTLP."""

    def __init__(self) -> None:
        self.provider = self._build_provider()

    def _build_provider(self) -> LoggerProvider:
        """
        Return LoggerProvider for exporting logs via OTLP.

        Re-use an existing provider if one has already been created. Otherwise, create
        a new provider and set it as the global provider.

        The provider is flushed on exit so we can include logs from short-lived processes,
        i.e. the CLI.
        """
        existing_provider = get_logger_provider()
        if isinstance(existing_provider, LoggerProvider):
            return existing_provider

        exporter = OTLPLogExporter()
        processor = BatchLogRecordProcessor(exporter)
        provider = LoggerProvider(resource=Resource.create())
        provider.add_log_record_processor(processor)
        set_logger_provider(provider)
        atexit.register(provider.shutdown)
        return provider

    def __call__(self, message: Message) -> None:
        """Emit a loguru record to the OTel collector."""
        record = message.record
        severity_text = record["level"].name
        severity_number = LOGURU_TO_OTEL[severity_text]

        # loguru stores time in seconds; OTel expected it in nanoseconds
        timestamp_ns = int(record["time"].timestamp() * 1e9)

        # Make bound fields top-level attributes so they can be directly queried when filtering
        # logs.
        attributes: dict[str, object] = dict(record["extra"])
        attributes["code.filepath"] = record["file"].path
        attributes["code.lineno"] = record["line"]
        attributes["code.function"] = record["function"]

        exception = record["exception"]
        self.provider.get_logger(record["name"]).emit(
            timestamp=timestamp_ns,
            severity_number=severity_number,
            severity_text=severity_text,
            body=record["message"],
            attributes=attributes,
            exception=exception.value if exception else None,
        )
