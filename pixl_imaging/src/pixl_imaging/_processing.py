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
from __future__ import annotations

import logging
import os
from asyncio import sleep
from dataclasses import dataclass
from time import time
from typing import TYPE_CHECKING, Any

from core.dicom_tags import DICOM_TAG_PROJECT_NAME
from decouple import config

from pixl_imaging._orthanc import Orthanc, PIXLRawOrthanc

if TYPE_CHECKING:
    from core.patient_queue.message import Message

logger = logging.getLogger("uvicorn")
logger.setLevel(os.environ.get("LOG_LEVEL", "WARNING"))


async def process_message(message: Message) -> None:
    """Process message from queue."""
    logger.debug("Processing: %s", message)

    study = ImagingStudy.from_message(message)
    orthanc_raw = PIXLRawOrthanc()

    existing_resource_ids = study.query_local(orthanc_raw)
    if len(existing_resource_ids) > 0:
        orthanc_raw.send_existing_study_to_anon(existing_resource_ids[0])
        return

    # Tell orthanc to query VNA for the patient and accession number
    query_id = orthanc_raw.query_remote(study.orthanc_query_dict, modality=config("VNAQR_MODALITY"))
    if query_id is None:
        logger.error("Failed to find %s in the VNA", study)
        raise RuntimeError

    # Get image from VNA for patient and accession number
    job_id = orthanc_raw.retrieve_from_remote(query_id=query_id)  # C-Move
    job_state = "Pending"
    start_time = time()

    while job_state != "Success":
        if (time() - start_time) > config("PIXL_DICOM_TRANSFER_TIMEOUT", cast=float):
            msg = (
                f"Failed to transfer {message} within "
                f"{config('PIXL_DICOM_TRANSFER_TIMEOUT')} seconds"
            )
            raise TimeoutError(msg)

        await sleep(0.1)
        job_state = orthanc_raw.job_state(job_id=job_id)

    # Now that instance has arrived in orthanc raw, we can set its project name tag via the API
    studies_with_tags = orthanc_raw.query_local(study.orthanc_query_dict)
    logger.info("Local instances with matching tags: %s", studies_with_tags)

    if len(studies_with_tags) != 1:
        logger.error(
            "Got %s studies with matching accession number and patient ID, expected 1",
            len(studies_with_tags),
        )

    for study in studies_with_tags:
        logger.info("Study ID %s", study)
        orthanc_raw.modify_private_tags_by_study(
            study_id=study,
            private_creator=DICOM_TAG_PROJECT_NAME.creator_string,
            tag_replacement={
                # The tag here needs to be defined in orthanc's dictionary
                DICOM_TAG_PROJECT_NAME.tag_nickname: message.project_name,
            },
        )

    return


@dataclass
class ImagingStudy:
    """Dataclass for DICOM study unique to a patient and imaging study"""

    message: Message

    @classmethod
    def from_message(cls, message: Message) -> ImagingStudy:
        """Build an imaging study from a queue message."""
        return ImagingStudy(message=message)

    @property
    def orthanc_query_dict(self) -> dict:
        """Build a dictionary to query a study."""
        return {
            "Level": "Study",
            "Query": {
                "PatientID": self.message.mrn,
                "AccessionNumber": self.message.accession_number,
            },
        }

    def query_local(self, node: Orthanc) -> Any:
        """Does this study exist in an Orthanc instance/node?"""
        return node.query_local(self.orthanc_query_dict)
