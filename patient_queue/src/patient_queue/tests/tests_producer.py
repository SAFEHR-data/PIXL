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
from time import sleep

TEST_URL = "localhost"
TEST_PORT = 5672
TEST_QUEUE = "test"


def test_create_pixl_producer() -> None:
    """Checks that PixlProducer can be instantiated."""
    pp = PixlProducer(host=TEST_URL, port=TEST_PORT, queue_name=TEST_QUEUE)
    pp.connect()
    assert pp.connection.is_open
    pp.close()


def test_publish() -> None:
    pp = PixlProducer(host=TEST_URL, port=TEST_PORT, queue_name=TEST_QUEUE)
    pp.connect()
    pp.publish(msgs=["test"])
    sleep(10)
    assert pp._queue.method.message_count == 1
    pp.clear_queue()
    pp.close()


