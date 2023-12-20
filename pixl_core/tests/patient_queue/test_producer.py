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
import pytest
from core.patient_queue.message import Message
from core.patient_queue.producer import PixlProducer

TEST_QUEUE = "test_publish"
TEST_MESSAGE = Message(
    mrn="111",
    accession_number="123",
    study_datetime="2022-11-22T13:33:00+00:00",
    procedure_occurrence_id="234",
    project_name="test project",
    omop_es_timestamp="2023-12-07T14:08:00+00:00",
)


@pytest.mark.pika()
def test_create_pixl_producer() -> None:
    """Checks that PixlProducer can be instantiated."""
    with PixlProducer(queue_name=TEST_QUEUE) as pp:
        assert pp.connection_open


@pytest.mark.pika()
def test_publish() -> None:
    """
    Checks that after publishing, there is one message in the queue.
    Will only work if nothing has been added to queue before.
    """
    with PixlProducer(queue_name=TEST_QUEUE) as pp:
        pp.clear_queue()
        pp.publish(messages=[TEST_MESSAGE])

    with PixlProducer(queue_name=TEST_QUEUE) as pp:
        assert pp.message_count == 1
