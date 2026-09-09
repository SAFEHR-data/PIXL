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

if TYPE_CHECKING:
    from datetime import date, datetime


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
