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
from __future__ import annotations

import datetime

from core.patient_queue.message import Message, deserialise

msg = Message(
    mrn="111",
    accession_number="123",
    study_date=datetime.date.fromisoformat("2022-11-22"),
    procedure_occurrence_id="234",
    project_name="test project",
    omop_es_timestamp=datetime.datetime.strptime("Dec 7 2023 2:08PM", "%b %d %Y %I:%M%p").replace(
        tzinfo=datetime.timezone.utc
    ),
)


def test_serialise() -> None:
    """Checks that messages can be correctly serialised"""
    msg_body = msg.serialise(deserialisable=False)
    assert (
        msg_body == b'{"mrn": "111", "accession_number": "123", '
        b'"study_date": "2022-11-22", '
        b'"procedure_occurrence_id": "234", '
        b'"project_name": "test project", '
        b'"omop_es_timestamp": "2023-12-07T14:08:00+00:00"}'
    )


def test_deserialise() -> None:
    """Checks if deserialised messages are the same as the original"""
    serialised_msg = msg.serialise()
    assert deserialise(serialised_msg) == msg
