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
"""Data classes to represent imaging and anonymisation messages in their respective queues."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from jsonpickle import encode

if TYPE_CHECKING:
    from datetime import date, datetime

from loguru import logger


@dataclass
class ImagingRequestMessage:
    """Data containing the information to identify a DICOM study for an imaging request."""

    mrn: str
    accession_number: str
    study_uid: str
    series_uid: str
    study_date: date
    procedure_occurrence_id: int
    project_name: str
    extract_generated_timestamp: datetime

    @property
    def identifier(self) -> str:
        """Identifier for message"""
        return (
            f"Message({self.mrn=} {self.accession_number=} {self.study_uid=} {self.series_uid=}"
        ).replace("self.", "")

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


@dataclass
class AnonymisationMessage:
    """Data containing the information to identify an anonymisation request."""

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
