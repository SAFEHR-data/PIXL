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
import os
from unittest import TestCase
from pathlib import Path

from patient_queue.producer import PixlProducer
from patient_queue.subscriber import PixlConsumer
from patient_queue.subscriber import PixlBlockingConsumer
import pytest
from token_buffer.tokens import TokenBucket

TEST_URL = "queue"
TEST_PORT = 5672
TEST_QUEUE = "test_consume"
RABBIT_USER = os.environ["RABBITMQ_DEFAULT_USER"]
RABBIT_PASSWORD = os.environ["RABBITMQ_DEFAULT_PASS"]

counter = 0


@pytest.fixture(scope="class")
def event_loop_instance(request):
    """ Add the event_loop as an attribute to the unittest style test class. """
    request.cls.event_loop = asyncio.get_event_loop_policy().new_event_loop()
    yield
    request.cls.event_loop.close()


@pytest.mark.usefixtures("event_loop_instance")
class TestConsumer(TestCase):
    def get_async_result(self, coro):
        """ Run a coroutine synchronously. """
        return self.event_loop.run_until_complete(coro)

    async def test_create(self) -> None:
        """Checks consume is working."""
        global counter
        with PixlProducer(
            host=TEST_URL,
            port=TEST_PORT,
            queue_name=TEST_QUEUE,
            user=RABBIT_USER,
            password=RABBIT_PASSWORD,
        ) as pp:
            pp.publish(msgs=["test"])

        async with PixlConsumer(
            queue=TEST_QUEUE, port=TEST_PORT, token_bucket=TokenBucket(), host=TEST_URL
        ) as pc:

            def consume(msg: bytes) -> None:
                if str(msg) != "":
                    global counter
                    counter += 1
                    return counter

            result = self.get_async_result(callback=consume)

        assert counter == 1


def test_consume_all() -> None:
    """Checks that all messages are returned that have been published before for graceful shutdown."""
    with PixlProducer(
        host=TEST_URL,
        port=TEST_PORT,
        queue_name=TEST_QUEUE,
        user=RABBIT_USER,
        password=RABBIT_PASSWORD,
    ) as pp:
        pp.publish(msgs=["test", "test"])

    with PixlBlockingConsumer(
        host=TEST_URL,
        port=TEST_PORT,
        queue_name=TEST_QUEUE,
        user=RABBIT_USER,
        password=RABBIT_PASSWORD,
    ) as bc:

        counter_bc = bc.consume_all(
            timeout_in_seconds=2, file_path=Path("test_producer.csv")
        )
        assert counter_bc == 2
