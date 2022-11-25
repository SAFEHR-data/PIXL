#  Copyright (c) University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from dataclasses import dataclass
from datetime import datetime
import logging
import os

from pixl_pacs._orthanc import Orthanc, PIXLRawOrthanc
from pixl_pacs.utils import env_var

logger = logging.getLogger("uvicorn")
logger.setLevel(os.environ.get("LOG_LEVEL", "WARNING"))


def process_message(message_body: bytes) -> None:
    logger.info(f"Processing: {message_body.decode()}")

    study = ImagingStudy.from_message(message_body)
    orthanc_raw = PIXLRawOrthanc()

    if study.exists_in(orthanc_raw):
        logger.info("Study exists in cache")
        return

    query_id = orthanc_raw.query_remote(
        study.orthanc_query_dict, modality=env_var("VNAQR_MODALITY")
    )
    if query_id is None:
        logger.error(f"Failed to find {study} in the VNA")
        raise RuntimeError

    orthanc_raw.retrieve_from_remote(query_id=query_id)  # C-Move

    # poll for completion


@dataclass
class ImagingStudy:
    """Dataclass for EHR unique to a patient and xray study"""

    mrn: str
    accession_number: str
    study_datetime: datetime

    @classmethod
    def from_message(cls, message_body: bytes) -> "ImagingStudy":
        data = deserialise(message_body)
        return ImagingStudy(**data)

    @property
    def orthanc_query_dict(self) -> dict:
        return {
            "Level": "Study",
            "Query": {"PatientID": self.mrn, "AccessionNumber": self.accession_number},
        }

    def exists_in(self, node: Orthanc) -> bool:
        """Does this study exist in an Orthanc instance/node?"""
        return len(node.query_local(self.orthanc_query_dict)) > 0


# TODO: move to patient queue package
def deserialise(message_body: bytes) -> dict:
    logger.debug(f"De-serialising: {message_body.decode()}")

    parts = message_body.decode().split(",")
    return {
        "mrn": parts[0],
        "accession_number": parts[1],
        "study_datetime": datetime.strptime(parts[2], "%d/%m/%Y %H:%M:%S"),
    }
