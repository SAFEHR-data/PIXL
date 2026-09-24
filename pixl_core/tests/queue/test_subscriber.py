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
from __future__ import annotations

import asyncio
from unittest.mock import ANY, AsyncMock, Mock

import pytest

from core.exceptions import (
    PixlDiscardError,
    PixlOutOfHoursError,
    PixlRequeueMessageError,
)
from core.queue.producer import AnonymisationProducer, PixlProducer
from core.queue.subscriber import AnonymisationPixlConsumer, PixlConsumer
from core.token_buffer.tokens import TokenBucket

TEST_QUEUE = "test_consume"
TEST_QUEUE_ANON = "test_anon_consume"


class ExpectedTestError(Exception):
    """Expected error for testing."""


# Shared by both PixlConsumer and AnonymisationPixlConsumer error-handling tests below,
# so the two consumers' behaviour for a given error can't silently drift apart.
ERROR_HANDLING_CASES = [
    pytest.param(PixlRequeueMessageError, "reject", {"requeue": True}, id="requeue"),
    pytest.param(PixlOutOfHoursError, "nack", {"requeue": True}, id="out_of_hours"),
    pytest.param(PixlDiscardError, "ack", {}, id="discard"),
    pytest.param(ExpectedTestError, "ack", {}, id="unexpected"),
]


@pytest.mark.asyncio
@pytest.mark.usefixtures("run_containers")
@pytest.mark.xfail(
    reason="Sanity check that async test gets run", strict=True, raises=ExpectedTestError
)
async def test_create(mock_message) -> None:
    """Checks consume is working."""
    with PixlProducer(queue_name=TEST_QUEUE) as producer:
        producer.publish(messages=[mock_message], priority=1)

    consume = AsyncMock()
    async with PixlConsumer(
        queue_name=TEST_QUEUE,
        token_bucket=TokenBucket(),
        token_bucket_key="primary",  # noqa: S106
        callback=consume,
    ) as consumer:
        # Create a Task to run pc.run in the background
        task = asyncio.create_task(consumer.run())
        # Wait for a short time to allow pc.run to start
        await asyncio.sleep(1)
        # Cancel before assertion so the task doesn't hang
        task.cancel()
        # need to close the connection and channel
        await consumer._channel.close()
        await consumer._connection.close()
        consume.assert_called_once()
    # Fail on purpose to check async test awaited
    raise ExpectedTestError


@pytest.mark.asyncio
@pytest.mark.usefixtures("run_containers")
async def test_run_anon(mock_anon_message) -> None:
    """Checks that the consumer starts consuming messages."""
    with AnonymisationProducer(queue_name=TEST_QUEUE_ANON) as producer:
        producer.publish(messages=[mock_anon_message])

    callback = AsyncMock()
    async with AnonymisationPixlConsumer(
        queue_name=TEST_QUEUE_ANON,
        callback=callback,
    ) as consumer:
        # Create a Task to run consumer.run in the background
        task = asyncio.create_task(consumer.run())
        # Wait for a short time to allow consumer.run to start and pick up the message
        await asyncio.sleep(1)
        # Cancel before assertion so the task doesn't hang
        task.cancel()
        # need to close the connection and channel
        await consumer._channel.close()
        await consumer._connection.close()
        callback.assert_called_once_with(mock_anon_message, ANY)


@pytest.mark.asyncio
async def test_process_message_anon(
    mock_anon_message, mock_incoming_message, anon_consumer
) -> None:
    """Checks that a received message is passed to the callback and acked."""
    callback = AsyncMock()
    consumer = anon_consumer(TEST_QUEUE_ANON, callback)
    message = mock_incoming_message(mock_anon_message.serialise())

    await consumer._process_message(message)

    callback.assert_awaited_once_with(mock_anon_message, ANY)
    message.ack.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(("error", "method_name", "expected_kwargs"), ERROR_HANDLING_CASES)
async def test_process_message_error_handling(  # noqa: PLR0913
    monkeypatch,
    mock_message,
    mock_incoming_message,
    error,
    method_name,
    expected_kwargs,
) -> None:
    """Each error type from the callback results in the correct ack/nack/reject call."""
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    callback = AsyncMock(side_effect=error)
    token_bucket = Mock(has_token=Mock(return_value=True))

    consumer = PixlConsumer(
        queue_name=TEST_QUEUE,
        token_bucket=token_bucket,
        token_bucket_key="primary",  # noqa: S106
        callback=callback,
    )
    message = mock_incoming_message(mock_message.serialise())

    await consumer._process_message(message)

    getattr(message, method_name).assert_awaited_once_with(**expected_kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize(("error", "method_name", "expected_kwargs"), ERROR_HANDLING_CASES)
async def test_process_message_anon_error_handling(  # noqa: PLR0913
    monkeypatch,
    mock_anon_message,
    mock_incoming_message,
    anon_consumer,
    error,
    method_name,
    expected_kwargs,
) -> None:
    """Each error type from the callback results in the correct ack/nack/reject call."""
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    callback = AsyncMock(side_effect=error)
    consumer = anon_consumer(TEST_QUEUE_ANON, callback)
    message = mock_incoming_message(mock_anon_message.serialise())

    await consumer._process_message(message)

    getattr(message, method_name).assert_awaited_once_with(**expected_kwargs)
