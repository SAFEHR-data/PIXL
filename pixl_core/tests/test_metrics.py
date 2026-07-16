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
"""Tests for PIXL custom OpenTelemetry metrics."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from core.metrics import (
    pixl_metrics,
    record_instance_deidentification_failure,
    record_study_deidentification_failure,
    record_study_exported,
)


@pytest.fixture
def mock_instruments(monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    """
    Replace each instrument on pixl_metrics with a Mock counter.

    Lets the record_* helpers be tested by asserting on the counter's `.add`
    calls, with no OTel provider or exporter involved.
    """
    mocks = {
        "studies_exported": Mock(),
        "deidentification_failures": Mock(),
        "instance_deidentification_failures": Mock(),
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(pixl_metrics, name, mock)
    return mocks


def test_record_study_exported(mock_instruments: dict[str, Mock]) -> None:
    """Test the exported-studies counter is incremented with the project attribute."""
    record_study_exported(project_name="test-project")

    mock_instruments["studies_exported"].add.assert_called_once_with(
        amount=1,
        attributes={"project_name": "test-project"},
    )


def test_record_study_deidentification_failure(mock_instruments: dict[str, Mock]) -> None:
    """Test the study de-id failure counter records project, type and message attributes."""
    record_study_deidentification_failure(
        project_name="test-project",
        failure_type="StringDataRightTruncation",
        message="value too long for type character varying(255)",
    )

    mock_instruments["deidentification_failures"].add.assert_called_once_with(
        amount=1,
        attributes={
            "project_name": "test-project",
            "type": "StringDataRightTruncation",
            "message": "value too long for type character varying(255)",
        },
    )


def test_record_instance_deidentification_failure(mock_instruments: dict[str, Mock]) -> None:
    """Test the instance de-id failure counter records the study_uid alongside the rest."""
    record_instance_deidentification_failure(
        project_name="test-project",
        study_uid="1.2.3",
        failure_type="ValueError",
        message="bad tag",
    )

    mock_instruments["instance_deidentification_failures"].add.assert_called_once_with(
        amount=1,
        attributes={
            "project_name": "test-project",
            "study_uid": "1.2.3",
            "type": "ValueError",
            "message": "bad tag",
        },
    )
