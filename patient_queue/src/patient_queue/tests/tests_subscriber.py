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

from time import sleep
from patient_queue.subscriber import PixlConsumer


def test_create() -> None:
    """Checks that PIXL producer can be instantiated."""
    pc = PixlConsumer(_queue="test")
    assert pc is not None
    pc.shutdown()


def test_create_msg(dummy_producer) -> None:
    """Checks that message can be produced on respective queue."""
    pc = PixlConsumer(_queue="test")
    # dummy_producer.create_entry(msg="test")
    sleep(10.0)
    body = pc.retrieve_msg()

    if body is not None:
        assert True
    else:
        assert False

    pc.shutdown()
