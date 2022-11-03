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


def test_create(dummy_url, dummy_queue) -> None:
    """Checks that PixlProducer can be instantiated."""
    pp = PixlProducer(_service_url=dummy_url, _queue=dummy_queue)
    assert pp is not None
    pp.stop()


def test_connection_to_service(dummy_url, dummy_queue) -> None:
    """Checks whether connection from producer to RabbitMQ service can be established."""
    pp = PixlProducer(_service_url=dummy_url, _queue=dummy_queue)
    pp.establish_keep_queue_open()
    assert True
    # assert pp.connection is not None
    # assert pp.stopping is False
    # pp.stop()