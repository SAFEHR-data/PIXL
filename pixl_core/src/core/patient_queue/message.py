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

"""Utility functions"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SerialisedMessage:
    """Class to represent a serialised message."""

    body: bytes

    def __init__(self, body: str) -> None:
        """Initialise the serialised message from JSON dump."""
        self.body = body.encode("utf-8")

    def deserialise(self) -> dict:
        """Returns the de-serialised message in JSON format."""
        logger.debug("De-serialising: %s", self.decode())
        data = dict(json.loads(self.decode()))
        if "study_datetime" in data:
            data["study_datetime"] = datetime.fromisoformat(data["study_datetime"])
        if "omop_es_timestamp" in data:
            data["omop_es_timestamp"] = datetime.fromisoformat(data["omop_es_timestamp"])

        return data

    def decode(self) -> str:
        """Returns the serialised message in string format."""
        return self.body.decode()


class Message:
    """Class to represent a message containing the relevant information for a study."""

    mrn: str
    accession_number: str
    study_datetime: datetime
    procedure_occurrence_id: str
    project_name: str
    omop_es_timestamp: datetime

    def __init__(self, message_fields: dict) -> None:
        """Initialise the message."""
        self.mrn = message_fields["mrn"]
        self.accession_number = message_fields["accession_number"]
        self.study_datetime = message_fields["study_datetime"]
        self.procedure_occurrence_id = message_fields["procedure_occurrence_id"]
        self.project_name = message_fields["project_name"]
        self.omop_es_timestamp = message_fields["omop_es_timestamp"]

    def serialise(self) -> "SerialisedMessage":
        """Serialise the message into JSON format."""
        msg = (
            "Serialising message with\n"
            " * patient id: %s\n"
            " * accession number: %s\n"
            " * timestamp: %s\n"
            " * procedure_occurrence_id: %s\n",
            " * project_name: %s\n * omop_es_timestamp: %s",
            self.mrn,
            self.accession_number,
            self.study_datetime,
            self.procedure_occurrence_id,
            self.project_name,
            self.omop_es_timestamp,
        )
        logger.debug(msg)

        body = json.dumps(
            {
                "mrn": self.mrn,
                "accession_number": self.accession_number,
                "study_datetime": self.study_datetime.isoformat(),
                "procedure_occurrence_id": self.procedure_occurrence_id,
                "project_name": self.project_name,
                "omop_es_timestamp": self.omop_es_timestamp.isoformat(),
            }
        )

        return SerialisedMessage(body=body)
