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

from patient_queue.producer import PixlProducer

TEST_URL = "localhost"
TEST_PORT = 5672
TEST_QUEUE = "test_publish"


def test_create_pixl_producer() -> None:
    """Checks that PixlProducer can be instantiated."""
    pp = PixlProducer(host=TEST_URL, port=TEST_PORT, queue_name=TEST_QUEUE)
    pp.connect()
    assert pp.connection.is_open
    pp.close()


def test_publish() -> None:
    """Checks that after publishing, there is one message in the queue. Will only work if nothing has been added to queue before."""
    pp = PixlProducer(host=TEST_URL, port=TEST_PORT, queue_name=TEST_QUEUE)
    pp.publish(msgs=["test"])
    pp.connect()
    assert pp._queue.method.message_count == 1
    pp.clear_queue()
    pp.close()


def test_consume_all() -> None:
    """Checks that all messages are returned that have been published before for graceful shutdown."""
    pp = PixlProducer(host=TEST_URL, port=TEST_PORT, queue_name=TEST_QUEUE)
    pp.publish(msgs=["test", "test"])
    msgs = pp.consume_all(timeout_in_seconds=2)

    counter = 0
    for msg in msgs:
        if all(arg is None for arg in msg):
            break
        else:
            counter += 1

    assert counter == 2
    pp.close()
