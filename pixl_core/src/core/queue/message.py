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
"""Classes to represent messages in the patient queue."""

from __future__ import annotations

from typing import Any

from jsonpickle import decode


def deserialise(serialised_msg: bytes) -> Any:
    """
    Deserialise a message from a bytes-encoded JSON string.
    If the message was serialised with `deserialisable=True`, the original Message object will be
    returned. Otherwise, a dictionary will be returned.

    :param serialised_msg: The serialised message.
    """
    return decode(serialised_msg)  # noqa: S301, since we control the input, so no security risks
