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
import os
import pytest

from token_buffer.tokens import TokenBucket
from patient_queue.subscriber import PixlConsumer
from patient_queue.producer import PixlProducer

TEST_URL = "localhost"
TEST_PORT = 5672
TEST_QUEUE = "test_consume"
RABBIT_USER = os.environ["RABBITMQ_DEFAULT_USER"]
RABBIT_PASSWORD = os.environ["RABBITMQ_DEFAULT_PASS"]

counter = 0


@pytest.mark.asyncio
async def test_create() -> None:
    global counter
    with PixlProducer(host=TEST_URL, port=TEST_PORT, queue_name=TEST_QUEUE, user=RABBIT_USER, password=RABBIT_PASSWORD) as pp:
        pp.publish(msgs=["test"])

    """Checks that PIXL producer can be instantiated."""
    async with PixlConsumer(queue=TEST_QUEUE, host=TEST_URL, port=TEST_PORT, token_bucket=TokenBucket()) as pc:
        def consume(msg: bytes) -> None:
            if str(msg) != "":
                global counter
                print(counter)
                counter += 1
        pc.run(callback=consume)

    assert counter == 1
