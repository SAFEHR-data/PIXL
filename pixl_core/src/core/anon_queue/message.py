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

from dataclasses import dataclass
from typing import Any

from jsonpickle import decode, encode
from loguru import logger


@dataclass
class AnonymisationMessage:
    """
    Representation of a RabbitMQ message containing the information
    to identify an anonymisation request.
    """

    resource_ids: list[str]
    study_uids: list[str]
    series_uids: list[str]
    project_name: str

    @property
    def identifier(self) -> str:
        """Identifier for message"""
        return (f"Message({self.resource_ids=} {self.study_uids=} {self.series_uids=}").replace(
            "self.", ""
        )

    def serialise(self, *, deserialisable: bool = True) -> bytes:
        """
        Serialise the message into a JSON string and convert to bytes.

        :param deserialisable: If True, the serialised message will be deserialisable, by setting
            the unpicklable flag to False in jsonpickle.encode(), meaning that the original Message
            object can be recovered by `deserialise()`. If False, calling `deserialise()` on the
            serialised message will return a dictionary.
        """
        logger.trace("Serialising {}", self)
        return str.encode(encode(self, unpicklable=deserialisable))


def deserialise(serialised_msg: bytes) -> Any:
    """
    Deserialise a message from a bytes-encoded JSON string.
    If the message was serialised with `deserialisable=True`, the original Message object will be
    returned. Otherwise, a dictionary will be returned.

    :param serialised_msg: The serialised message.
    """
    return decode(serialised_msg)  # noqa: S301, since we control the input, so no security risks
