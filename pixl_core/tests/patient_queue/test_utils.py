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
import datetime
import json

from core.patient_queue.utils import deserialise, serialise


def test_serialise() -> None:
    """Checks that messages can be correctly serialised"""
    msg_body = serialise(
        mrn="111",
        accession_number="123",
        study_datetime=datetime.datetime.strptime("Nov 22 2022 1:33PM", "%b %d %Y %I:%M%p").replace(
            tzinfo=datetime.timezone.utc
        ),
        procedure_occurrence_id="234",
    )
    assert (
        msg_body.decode() == '{"mrn": "111", "accession_number": "123", '
        '"study_datetime": "2022-11-22T13:33:00+00:00", '
        '"procedure_occurrence_id": "234"}'
    )


def test_simple_deserialise() -> None:
    """Checks a simple JSON deserialise works"""
    assert deserialise((json.dumps({"key": "value"})).encode("utf-8"))["key"] == "value"


def test_deserialise_datetime() -> None:
    """Checks that datetimes can be correctly serialised"""
    timestamp = datetime.datetime.fromordinal(100012)
    data = deserialise(serialise(mrn="", accession_number="", study_datetime=timestamp, procedure_occurrence_id=""))
    assert data["study_datetime"] == timestamp
