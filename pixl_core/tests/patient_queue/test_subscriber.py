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
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from core.patient_queue.message import Message
from core.patient_queue.producer import PixlProducer
from core.patient_queue.subscriber import PixlBlockingConsumer, PixlConsumer
from core.token_buffer.tokens import TokenBucket

TEST_QUEUE = "test_consume"
TEST_MESSAGE = Message(
    mrn="111",
    accession_number="123",
    study_date="2022-11-22T13:33:00+00:00",
    procedure_occurrence_id="234",
    project_name="test project",
    omop_es_timestamp="2023-12-07T14:08:00+00:00",
)


@pytest.mark.asyncio()
@pytest.mark.usefixtures("run_containers")
async def test_create() -> None:
    """Checks consume is working."""
    with PixlProducer(queue_name=TEST_QUEUE) as pp:
        pp.publish(messages=[TEST_MESSAGE])
        pp.publish(messages=[TEST_MESSAGE])

    async with PixlConsumer(queue_name=TEST_QUEUE, token_bucket=TokenBucket()) as pc:
        consume = AsyncMock()
        # Create a Task to run pc.run in the background
        task = asyncio.create_task(pc.run(callback=consume))

        # Wait for a short time to allow pc.run to start
        await asyncio.sleep(1)

        consume.assert_called()
        task.cancel()
        # need to close connection attribute or cancellation will hang waiting for next message
        await pc._connection.close()  # noqa: SLF001
        await asyncio.sleep(1)  # Allow time for task to cancel
    # pytest.fail("Check that async test runs")  # noqa: ERA001 uncomment for sanity check


@pytest.mark.usefixtures("run_containers")
def test_consume_all() -> None:
    """
    Checks that all messages are returned that have been published before for
    graceful shutdown.
    """
    with PixlProducer(queue_name=TEST_QUEUE) as pp:
        pp.publish(messages=[TEST_MESSAGE, TEST_MESSAGE])

    with PixlBlockingConsumer(queue_name=TEST_QUEUE) as bc:
        counter_bc = bc.consume_all(timeout_in_seconds=2, file_path=Path("test_producer.csv"))
        assert counter_bc == 2
