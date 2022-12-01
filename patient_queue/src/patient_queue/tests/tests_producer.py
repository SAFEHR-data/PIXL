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
from pathlib import Path

from patient_queue.producer import PixlProducer

TEST_URL = "queue"
TEST_PORT = 5672
TEST_QUEUE = "test_publish"
RABBIT_USER = os.environ["RABBITMQ_DEFAULT_USER"]
RABBIT_PASSWORD = os.environ["RABBITMQ_DEFAULT_PASS"]


def test_create_pixl_producer() -> None:
    """Checks that PixlProducer can be instantiated."""
    with PixlProducer(
        host=TEST_URL,
        port=TEST_PORT,
        queue_name=TEST_QUEUE,
        user=RABBIT_USER,
        password=RABBIT_PASSWORD,
    ) as pp:
        assert pp.connection_open


def test_publish() -> None:
    """Checks that after publishing, there is one message in the queue. Will only work if nothing has been added to queue before."""
    with PixlProducer(
        host=TEST_URL,
        port=TEST_PORT,
        queue_name=TEST_QUEUE,
        user=RABBIT_USER,
        password=RABBIT_PASSWORD,
    ) as pp:
        pp.publish(msgs=["test"])

    with PixlProducer(
        host=TEST_URL,
        port=TEST_PORT,
        queue_name=TEST_QUEUE,
        user=RABBIT_USER,
        password=RABBIT_PASSWORD,
    ) as pp:
        assert pp.queue.method.message_count == 1
        pp.clear_queue()
