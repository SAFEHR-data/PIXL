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

from core.anon_queue.message import deserialise


def test_serialise(mock_anon_message) -> None:
    """Checks that messages can be correctly serialised"""
    msg_body = mock_anon_message.serialise(deserialisable=False)
    assert (
        msg_body == b'{"resource_ids": ["resource-1", "resource-2"], '
        b'"study_uids": ["1.2.3", "4.5.6"], '
        b'"series_uids": ["1.2.3.1", "1.2.3.2"], '
        b'"project_name": "test project"}'
    )


def test_deserialise(mock_message) -> None:
    """Checks if deserialised messages are the same as the original"""
    serialised_msg = mock_message.serialise()
    assert deserialise(serialised_msg) == mock_message
