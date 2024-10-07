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
from unittest.mock import AsyncMock

import pytest
from core.patient_queue.producer import PixlProducer
from core.patient_queue.subscriber import PixlConsumer
from core.token_buffer.tokens import TokenBucket

TEST_QUEUE = "test_consume"


class ExpectedTestError(Exception):
    """Expected error for testing."""


@pytest.mark.asyncio()
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
        await consumer._channel.close()  # noqa: SLF001
        await consumer._connection.close()  # noqa: SLF001
        consume.assert_called_once()
    # Fail on purpose to check async test awaited
    raise ExpectedTestError
