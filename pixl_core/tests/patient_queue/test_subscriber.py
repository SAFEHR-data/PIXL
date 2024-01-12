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
from typing import TYPE_CHECKING, Any
from unittest import TestCase

import pytest
from core.patient_queue.message import Message
from core.patient_queue.producer import PixlProducer
from core.patient_queue.subscriber import PixlBlockingConsumer, PixlConsumer
from core.token_buffer.tokens import TokenBucket

if TYPE_CHECKING:
    from collections.abc import Coroutine, Generator

TEST_QUEUE = "test_consume"
TEST_MESSAGE = Message(
    mrn="111",
    accession_number="123",
    study_date="2022-11-22T13:33:00+00:00",
    procedure_occurrence_id="234",
    project_name="test project",
    omop_es_timestamp="2023-12-07T14:08:00+00:00",
)

counter = 0


@pytest.fixture(scope="class")
def _event_loop_instance(request: Any) -> Generator:
    """
    Add the event_loop as an attribute to the unittest style test class.
    :param request: the object event loop ties to
    :returns: a generator
    """
    request.cls.event_loop = asyncio.get_event_loop_policy().new_event_loop()
    yield
    request.cls.event_loop.close()


@pytest.mark.usefixtures("_event_loop_instance")
class TestConsumer(TestCase):  # noqa: D101
    def get_async_result(self, coro: Coroutine) -> Any:
        """
        Run a coroutine synchronously.
        :param coro: coroutine generated from run
        """
        return self.event_loop.run_until_complete(coro)

    async def test_create(self) -> None:
        """Checks consume is working."""
        global counter  # noqa: PLW0602
        with PixlProducer(queue_name=TEST_QUEUE) as pp:
            pp.publish(messages=[TEST_MESSAGE])

        async with PixlConsumer(queue_name=TEST_QUEUE, token_bucket=TokenBucket()) as pc:

            async def consume(msg: Message) -> None:
                """
                Increases counter when message is downloaded.
                :param msg: body of the message, though not needed
                :returns: the increased counter, though here only once
                """
                if str(msg.serialise()) != "":
                    global counter
                    counter += 1

            self.get_async_result(pc.run(callback=consume))

        assert counter == 1


@pytest.mark.usefixtures("_run_containers")
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
