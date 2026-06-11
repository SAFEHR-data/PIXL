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
"""Logging configuration for PIXL services."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from loguru import Message

logging.addLevelName(5, "TRACE")
logging.addLevelName(25, "SUCCESS")


class StandardLibrarySink:
    """Forwards loguru records to stdlib logging so they reach the OTel LoggingHandler."""

    def __call__(self, message: Message) -> None:
        """Forward a loguru message to the stdlib logger of the same name."""
        record = message.record
        logging.getLogger(record["name"]).log(
            record["level"].no,
            record["message"],
            extra={"otel_attrs": record["extra"]},
        )


def configure_logging(level: str = "INFO") -> None:
    """Configure loguru and stdlib logging for all PIXL services."""
    logger.remove()
    logger.add(sys.stderr, level=level.upper())
    logger.add(StandardLibrarySink(), level=level.upper())

    root = logging.getLogger()
    # Preserve any OTel LoggingHandler added by opentelemetry-instrument before
    # app startup; remove only StreamHandlers.
    root.handlers[:] = [h for h in root.handlers if not isinstance(h, logging.StreamHandler)]
    root.setLevel(level.upper())
