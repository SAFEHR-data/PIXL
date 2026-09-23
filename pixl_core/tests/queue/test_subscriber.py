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
from core.queue.producer import PixlProducer
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


@pytest.mark.usefixtures("run_containers")
def test_run_anon() -> None:
    """Checks that the consumer starts consuming messages."""
    callback = Mock()

    with AnonymisationPixlConsumer(
        queue_name=TEST_QUEUE_ANON,
        callback=callback,
    ) as consumer:
        consumer._channel.basic_consume = Mock()
        consumer._channel.start_consuming = Mock()

        consumer.run()

        consumer._channel.basic_consume.assert_called_once_with(
            queue=TEST_QUEUE_ANON,
            on_message_callback=consumer._process_message,
            auto_ack=False,
        )
        consumer._channel.start_consuming.assert_called_once()


@pytest.mark.usefixtures("run_containers")
def test_process_message_anon(mock_anon_message) -> None:
    """A received message is passed to the callback and settled only when it asks."""
    callback = Mock()

    with AnonymisationPixlConsumer(
        queue_name=TEST_QUEUE_ANON,
        callback=callback,
    ) as consumer:
        channel = Mock()
        method = Mock(delivery_tag=1)
        properties = Mock(headers={})
        body = mock_anon_message.serialise()

        consumer._process_message(channel, method, properties, body)

        callback.assert_called_once_with(mock_anon_message, ANY, ANY, ANY)
        channel.basic_ack.assert_not_called()
        channel.basic_nack.assert_not_called()

        ack, nack = callback.call_args.args[2:]
        scheduled: list = []
        consumer._connection.add_callback_threadsafe = Mock(side_effect=scheduled.append)
        real_channel = consumer._channel
        consumer._channel = Mock(is_open=True)
        try:
            ack()
            scheduled[0]()
            consumer._channel.basic_ack.assert_called_once_with(delivery_tag=1)

            nack()
            scheduled[1]()
            consumer._channel.basic_nack.assert_called_once_with(delivery_tag=1, requeue=False)
        finally:
            consumer._channel = real_channel


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


@pytest.mark.parametrize(("error", "method_name", "expected_kwargs"), ERROR_HANDLING_CASES)
def test_process_message_anon_error_handling(  # noqa: PLR0913
    monkeypatch, mock_anon_message, anon_consumer, error, method_name, expected_kwargs
) -> None:
    """Each error type from the callback results in the correct ack/nack/reject call."""
    monkeypatch.setattr("core.queue.subscriber.time.sleep", Mock())
    callback = Mock(side_effect=error)
    consumer = anon_consumer(TEST_QUEUE_ANON, callback)

    channel = Mock()
    method = Mock(delivery_tag=1)
    properties = Mock(headers={})

    consumer._process_message(channel, method, properties, mock_anon_message.serialise())

    getattr(channel, f"basic_{method_name}").assert_called_once_with(
        delivery_tag=1, **expected_kwargs
    )
