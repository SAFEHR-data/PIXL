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
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


def deserialise(message_body: bytes) -> dict:
    """Returns the de-serialised message in JSON format."""
    logger.debug(f"De-serialising: {message_body.decode()}")
    return json.loads(message_body.decode())


def serialise(mrn: str, acsn_no: str, date: datetime):
    """Returns serialised message from patient id, accession number and date of study.
    :param mrn: patient identifier
    :param acsn_no: accession number
    :param date: date of the study
    :returns: JSON formatted message"""
    logger.debug(f"Serialising message with patient id {mrn}, accession number: {acsn_no} and date {date}")
    return json.dumps({'mrn': mrn, 'accession_number': acsn_no, 'date': date}, default=str)

