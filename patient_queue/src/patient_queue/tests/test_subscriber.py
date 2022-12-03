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
import asyncio
from pathlib import Path
from typing import Any, Coroutine, Generator
from unittest import TestCase

from patient_queue.producer import PixlProducer
from patient_queue.subscriber import PixlBlockingConsumer, PixlConsumer
import pytest
from token_buffer.tokens import TokenBucket

TEST_QUEUE = "test_consume"
MESSAGE_BODY = "test".encode("utf-8")
counter = 0


@pytest.fixture(scope="class")
def event_loop_instance(request: Any) -> Generator:
    """Add the event_loop as an attribute to the unittest style test class.
    :param request: the object event loop ties to
    :returns: a generator"""
    request.cls.event_loop = asyncio.get_event_loop_policy().new_event_loop()
    yield
    request.cls.event_loop.close()


@pytest.mark.usefixtures("event_loop_instance")
class TestConsumer(TestCase):
    def get_async_result(self, coro: Coroutine) -> Any:
        """Run a coroutine synchronously.
        :param coro: coroutine generated from run"""
        return self.event_loop.run_until_complete(coro)  # type: ignore

    async def test_create(self) -> None:
        """Checks consume is working."""
        global counter
        with PixlProducer(queue_name=TEST_QUEUE) as pp:
            pp.publish(messages=[MESSAGE_BODY])

        async with PixlConsumer(
            queue_name=TEST_QUEUE, token_bucket=TokenBucket()
        ) as pc:

            async def consume(msg: bytes) -> None:
                """
                Increases counter when message is downloaded.
                :param msg: body of the message, though not needed
                :returns: the increased counter, though here only once
                """
                if str(msg) != "":
                    global counter
                    counter += 1

            self.get_async_result(pc.run(callback=consume))

        assert counter == 1


def test_consume_all() -> None:
    """Checks that all messages are returned that have been published before for
    graceful shutdown."""
    with PixlProducer(queue_name=TEST_QUEUE) as pp:
        pp.publish(messages=[MESSAGE_BODY, MESSAGE_BODY])

    with PixlBlockingConsumer(queue_name=TEST_QUEUE) as bc:
        counter_bc = bc.consume_all(
            timeout_in_seconds=2, file_path=Path("test_producer.csv")
        )
        assert counter_bc == 2
