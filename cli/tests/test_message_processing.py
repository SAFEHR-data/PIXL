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

"""Test message processing module."""

import os
from collections.abc import Generator
from unittest.mock import AsyncMock, Mock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from core.queue.models import AnonymisationMessage
from core.queue.producer import PixlProducer
from pixl_cli._message_processing import (
    _message_count,
    retry_until_export_count_is_unchanged,
)
from pixl_imaging._orthanc import PIXLAnonOrthanc


@pytest.fixture
def _zero_message_count(monkeypatch: MonkeyPatch) -> None:
    """Ensure that message count is always zero, so that we don't have to deal with rabbitmq"""
    monkeypatch.setattr("pixl_cli._message_processing._message_count", lambda _: 0)


@pytest.fixture
def mock_publisher(mocker) -> Generator[Mock, None, None]:
    """Patched publisher that does nothing, returns MagicMock of the publish method."""
    mocker.patch.object(PixlProducer, "__init__", return_value=None)
    mocker.patch.object(PixlProducer, "__enter__", return_value=PixlProducer)
    mocker.patch.object(PixlProducer, "__exit__")
    return mocker.patch.object(PixlProducer, "publish")


@pytest.mark.usefixtures("_zero_message_count")
def test_no_retry_if_none_exported(example_messages_df, db_session, mock_publisher):
    """
    GIVEN no images have been exported before starting, and num_retries set to 5
    WHEN rabbitmq messages set to zero and no messages are published to queue
    THEN populate_queue_and_db should never be called
    """
    os.environ["CLI_RETRY_SECONDS"] = "1"

    retry_until_export_count_is_unchanged(
        example_messages_df,
        num_retries=5,
        queues_to_populate=["imaging-primary"],
        messages_priority=1,
    )

    mock_publisher.assert_not_called()


@pytest.mark.usefixtures("_zero_message_count")
def test_retry_with_image_exported_and_no_change(
    example_messages_df, rows_in_session, mock_publisher
):
    """
    GIVEN one image already has been exported, and num_retries set to 5
    WHEN rabbitmq messages set to zero and no messages are published to queue
    THEN populate_queue_and_db should be called once
    """
    os.environ["CLI_RETRY_SECONDS"] = "1"

    retry_until_export_count_is_unchanged(
        example_messages_df,
        num_retries=5,
        queues_to_populate=["imaging-primary"],
        messages_priority=1,
    )

    mock_publisher.assert_called_once()


@pytest.mark.usefixtures("_zero_message_count")
def test_retry_with_image_exported_and_no_change_multiple_projects(
    example_messages_multiple_projects_df, rows_in_session, mock_publisher
):
    """
    GIVEN one image across two projects has been exported, and num_retries set to 5
    WHEN rabbitmq messages set to zero and no messages are published to queue
    THEN populate_queue_and_db should be called once
    """
    os.environ["CLI_RETRY_SECONDS"] = "1"

    retry_until_export_count_is_unchanged(
        example_messages_multiple_projects_df,
        num_retries=5,
        queues_to_populate=["imaging-primary"],
        messages_priority=1,
    )

    mock_publisher.assert_called_once()


def test_message_count_includes_anonymisation(mocker) -> None:
    """Checks that the anonymisation queue is included when counting messages."""
    mock_rabbitmq = Mock()
    mock_rabbitmq.message_count = 0

    mock_interface = mocker.patch("pixl_cli._message_processing.PixlBlockingInterface")
    mock_interface.return_value.__enter__.return_value = mock_rabbitmq

    _message_count(["imaging-primary"])

    queue_names = {call.kwargs["queue_name"] for call in mock_interface.call_args_list}

    assert queue_names == {
        "imaging-primary",
        "imaging-secondary",
        "anonymisation",
    }


@pytest.mark.asyncio
async def test_notify_anon_publishes_anonymisation_message(monkeypatch) -> None:
    """Checks that anonymisation requests are published to RabbitMQ."""
    orthanc_raw = AsyncMock()
    orthanc_raw.get_local_study.side_effect = [
        {"MainDicomTags": {"StudyInstanceUID": "1.2.3"}},
        {"MainDicomTags": {"StudyInstanceUID": "4.5.6"}},
    ]

    producer = Mock()
    producer_context = Mock()
    producer_context.__enter__ = Mock(return_value=producer)
    producer_context.__exit__ = Mock(return_value=None)

    monkeypatch.setattr(
        "pixl_imaging._orthanc.AnonymisationProducer",
        Mock(return_value=producer_context),
    )

    orthanc_anon = PIXLAnonOrthanc()

    await orthanc_anon.notify_anon_to_retrieve_study_resources(
        orthanc_raw=orthanc_raw,
        resource_ids=["resource-1", "resource-2"],
        series_uid="1.2.3.1\\1.2.3.2",
        project_name="test project",
    )

    producer.publish.assert_called_once_with(
        [
            AnonymisationMessage(
                resource_ids=["resource-1", "resource-2"],
                series_uids=["1.2.3.1", "1.2.3.2"],
                study_uids=["1.2.3", "4.5.6"],
                project_name="test project",
            )
        ]
    )
