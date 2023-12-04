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


def deserialise(message_body: bytes) -> dict:
    """Returns the de-serialised message in JSON format."""
    logger.debug("De-serialising: %s", message_body.decode())
    data = dict(json.loads(message_body.decode()))
    if "study_datetime" in data:
        data["study_datetime"] = datetime.fromisoformat(data["study_datetime"])
    return data


def serialise(mrn: str, accession_number: str, study_datetime: datetime) -> bytes:
    """
    Returns serialised message from patient id, accession number and date of study.
    :param mrn: patient identifier
    :param accession_number: accession number
    :param study_datetime: date and time of the study
    :returns: JSON formatted message
    """
    logger.debug(
        "Serialising message with patient id %s, "
        "accession number: %s and timestamp %s",
        mrn,
        accession_number,
        study_datetime,
    )
    return json.dumps(
        {
            "mrn": mrn,
            "accession_number": accession_number,
            "study_datetime": study_datetime.isoformat(),
        }
    ).encode("utf-8")
