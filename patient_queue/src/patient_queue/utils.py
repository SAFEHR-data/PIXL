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

import logging
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


def deserialise(message_body: bytes) -> dict:
    logger.debug(f"De-serialising: {message_body.decode()}")

    parts = message_body.decode().split(",")
    return {
        "mrn": parts[0],
        "accession_number": parts[1],
        "study_datetime": datetime.strptime(parts[2], "%d/%m/%Y %H:%M:%S"),
    }
