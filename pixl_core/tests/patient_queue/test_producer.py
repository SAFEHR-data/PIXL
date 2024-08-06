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

import pytest
from core.patient_queue.producer import PixlProducer

TEST_QUEUE = "test_publish"


@pytest.mark.usefixtures("run_containers")
def test_create_pixl_producer() -> None:
    """Checks that PixlProducer can be instantiated."""
    with PixlProducer(queue_name=TEST_QUEUE) as pp:
        assert pp.connection_open


@pytest.mark.usefixtures("run_containers")
def test_publish(mock_message) -> None:
    """
    Checks that after publishing, there is one message in the queue.
    Will only work if nothing has been added to queue before.
    """
    with PixlProducer(queue_name=TEST_QUEUE) as pp:
        pp.clear_queue()
        pp.publish(messages=[mock_message])

    with PixlProducer(queue_name=TEST_QUEUE) as pp:
        assert pp.message_count == 1
