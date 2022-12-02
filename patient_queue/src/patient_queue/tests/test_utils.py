#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from datetime import datetime as dt
import json

from patient_queue.utils import deserialise, serialise


def test_serialise() -> None:
    msg_body = serialise(
        mrn="111",
        acsn_no="123",
        timestamp=dt.strptime("Nov 22 2022 1:33PM", "%b %d %Y %I:%M%p"),
    )
    assert (
        msg_body.decode()
        == '{"mrn": "111", "accession_number": "123", "timestamp": "2022-11-22 13:33:00"}'
    )


def test_deserialise() -> None:
    assert deserialise((json.dumps({"key": "value"})).encode("utf-8"))["key"] == "value"
