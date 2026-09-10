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
from unittest.mock import AsyncMock, Mock

import pytest

from core.queue.producer import PixlProducer
from core.queue.subscriber import AnonymisationPixlConsumer, PixlConsumer
from core.token_buffer.tokens import TokenBucket

TEST_QUEUE = "test_consume"
TEST_QUEUE_ANON = "test_anon_consume"


class ExpectedTestError(Exception):
    """Expected error for testing."""


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
    """Checks that a received message is passed to the callback."""
    callback = Mock()

    with AnonymisationPixlConsumer(
        queue_name=TEST_QUEUE_ANON,
        callback=callback,
    ) as consumer:
        message = Mock()
        message.body = mock_anon_message.serialise()

        consumer._process_message(message)

        callback.assert_called_once_with(mock_anon_message)
