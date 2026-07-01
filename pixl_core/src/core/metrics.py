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
"""Define custom metrics for PIXL."""

from __future__ import annotations

from dataclasses import dataclass

from opentelemetry import metrics

__all__ = [
    "initialise_metrics",
    "record_study_deidentification_failure",
    "record_study_exported",
]


@dataclass
class PixlMetrics:
    """Custom metrics for PIXL."""

    studies_exported: metrics.Counter | None = None
    deidentification_failures: metrics.Counter | None = None


pixl_metrics = PixlMetrics()


def initialise_metrics() -> None:
    """
    Initialise custom metrics for PIXL.

    This must be done after the metrics provider has been set up,
    otherwise the metrics will be no-ops.
    """
    meter = metrics.get_meter(__name__)

    pixl_metrics.studies_exported = meter.create_counter(
        name="pixl.studies.exported",
        description="Number of studies exported, by project.",
        unit="1",
    )

    description = (
        "Number of studies that failed to be de-identified, by project and failure reason."
    )
    pixl_metrics.deidentification_failures = meter.create_counter(
        name="pixl.studies.deidentification.failures",
        unit="1",
        description=description,
    )


def record_study_exported(project_name: str) -> None:
    """
    Record a study exported metric.

    Args:
        project_name (str): The name of the project for which the study was exported.

    """
    if pixl_metrics.studies_exported is None:
        return

    pixl_metrics.studies_exported.add(
        amount=1,
        attributes={"project_name": project_name},
    )


def record_study_deidentification_failure(project_name: str, reason: str) -> None:
    """
    Record a de-identification failure metric.

    Args:
        reason (str): The reason for the de-identification failure.
        project_name (str): The name of the project for which the de-identification failure occurred.

    """
    if pixl_metrics.deidentification_failures is None:
        return

    pixl_metrics.deidentification_failures.add(
        amount=1,
        attributes={"reason": reason, "project_name": project_name},
    )
