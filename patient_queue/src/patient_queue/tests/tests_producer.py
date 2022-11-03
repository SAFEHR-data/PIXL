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


def test_create() -> None:
    """Checks that PIXL producer can be instantiated."""
    pp = PixlProducer(_queue="test")
    assert pp is not None
    pp.shutdown()


def test_create_msg() -> None:
    """Checks that message can be produced on respective queue."""
    pp = PixlProducer(_queue="test")
    try:
        pp.create_entry(msg="hello world")
        assert True
    except Exception:
        assert False
    pp.shutdown()
