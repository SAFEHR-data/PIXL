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

import datetime
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Optional
from zoneinfo import ZoneInfo

from core.exceptions import PixlDiscardError, PixlOutOfHoursError, PixlStudyNotInPrimaryArchiveError
from decouple import config

from pixl_imaging._orthanc import Orthanc, PIXLAnonOrthanc, PIXLRawOrthanc

if TYPE_CHECKING:
    from core.patient_queue.message import Message

from loguru import logger


class DicomModality(StrEnum):
    primary = config("PRIMARY_DICOM_SOURCE_MODALITY")
    secondary = config("SECONDARY_DICOM_SOURCE_MODALITY")


async def process_message(message: Message, archive: DicomModality) -> None:
    """
    Process message from queue by retrieving a study with the given Patient and Accession Number.
    We may receive multiple messages with same Patient + Acc Num, either as retries or because
    they are needed for multiple projects.
    """
    logger.trace("Processing: {}. Querying {} archive.", message.identifier, archive.name)

    study = ImagingStudy.from_message(message)
    orthanc_raw = PIXLRawOrthanc()
    orthanc_anon = PIXLAnonOrthanc()
    await _process_message(
        study=study,
        orthanc_raw=orthanc_raw,
        archive=archive,
        orthanc_anon=orthanc_anon,
    )


async def _process_message(
    study: ImagingStudy,
    orthanc_raw: PIXLRawOrthanc,
    archive: DicomModality,
    orthanc_anon: PIXLAnonOrthanc,
) -> None:
    """
    Retrieve a study from the archives and send it to Orthanc Anon.

    Querying the archives:
    If 'archive' is 'secondary' and it's during working hours:
        - raise a PixlOutOfHoursError to have the message requeued
    If the study doesn't exist and 'archive' is primary:
        - publish the message to the secondary imaging queue
        - raise a PixlDiscardError
    If the study doesn't exist and 'archive' is secondary:
        - raise a PixlDiscardError

    Querying Orthanc Raw:
    If the study already exists in Orthanc Raw:
        - query the archive to determine whether any instances are missing
        - retrieve any missing instances
    If it doesn't already exist in Orthanc Raw:
        - query the archive for the study
        - retrieve the study from the VNA / PACS

    Then:
        - send the study to Orthanc Anon if ORTHANC_AUTOROUTE_RAW_TO_ANON is True
        - if the C-STORE operation to Orthanc Anon is successful, and
          ORTHANC_AUTOROUTE_ANON_TO_ENDPOINT is True, send the study to the appropriate destination
    """
    await orthanc_raw.raise_if_pending_jobs()

    if archive.name == "secondary" and (_is_daytime() or _is_weekend()):
        msg = "Not querying secondary archive during the daytime or on the weekend."
        raise PixlOutOfHoursError(msg)

    logger.info("Processing: {}. Querying {} archive.", study.message.identifier, archive.name)

    study_query_id = await _find_study_in_archive_or_raise(
        orthanc_raw=orthanc_raw,
        study=study,
        archive=archive,
    )

    existing_local_resources = await _get_study_resources(
        orthanc_raw=orthanc_raw,
        study=study,
    )

    if not existing_local_resources:
        await _retrieve_study(
            orthanc_raw=orthanc_raw,
            study_query_id=study_query_id,
        )
    else:
        await _retrieve_missing_instances(
            resources=existing_local_resources,
            orthanc_raw=orthanc_raw,
            study=study,
            study_query_id=study_query_id,
            modality=archive.value,
        )

    resources = await _get_study_resources(
        orthanc_raw=orthanc_raw,
        study=study,
    )

    if not orthanc_raw.autoroute_to_anon:
        logger.debug("Auto-routing to Orthanc Anon is not enabled. Not sending study {}", resources)
        return

    await orthanc_anon.notify_anon_to_retrieve_study_resources(
        orthanc_raw=orthanc_raw,
        resource_ids=resources,
        project_name=study.message.project_name,
    )


async def _get_study_resources(
    orthanc_raw: PIXLRawOrthanc,
    study: ImagingStudy,
) -> list[str]:
    """Get a list of existing resources for a study in Orthanc Raw."""
    existing_resources: list[str] = await study.query_local(orthanc_raw)

    logger.debug(
        'Found {} existing resources for study "{}"',
        existing_resources,
        study,
    )

    return existing_resources


async def _find_study_in_archive_or_raise(
    orthanc_raw: Orthanc,
    study: ImagingStudy,
    archive: DicomModality,
) -> str:
    """
    Query an archive for a study.

    If 'archive' is 'secondary' and it's during working hours:
        - raise a PixlOutOfHoursError to have the message requeued
    If the study doesn't exist, and 'archive' is primary:
        - raise a PixlStudyNotInPrimaryArchiveError if a secondary archive is defined
        - raise a PixlDiscardError if a secondary archive is not defined
    If the study doesn't exist and 'archive' is secondary:
        - raise a PixlDiscardError

    When querying an archive, the study is first queried using its UID it it's available.
    If the UID is an empty string, or if the study is not found, the study is queried using
    the MRN and accession number.

    """
    query_id = await _find_study_in_archive(
        orthanc_raw=orthanc_raw,
        study=study,
        modality=archive.value,
    )

    if query_id is not None:
        return query_id

    if archive.name == "secondary":
        msg = f"Failed to find study {study.message.identifier} in primary or secondary archive."
        raise PixlDiscardError(msg)

    if config("SECONDARY_DICOM_SOURCE_AE_TITLE") == config("PRIMARY_DICOM_SOURCE_AE_TITLE"):
        msg = (
            f"Failed to find study {study.message.identifier} in primary archive "
            "and SECONDARY_DICOM_SOURCE_AE_TITLE is the same as PRIMARY_DICOM_SOURCE_AE_TITLE."
        )
        raise PixlDiscardError(msg)

    msg = (
        f"Failed to find study {study.message.identifier} in primary archive, "
        "sending message to secondary imaging queue."
    )
    raise PixlStudyNotInPrimaryArchiveError(msg)


async def _find_study_in_archive(
    orthanc_raw: Orthanc,
    study: ImagingStudy,
    modality: str,
) -> Optional[str]:
    """
    Query the primary archive for the study using its UID.
    If UID is not available, query on MRN and accession number.
    """
    query_response = None
    if study.message.study_uid:
        query_response = await orthanc_raw.query_remote(
            data=study.orthanc_uid_query_dict,
            modality=modality,
        )
    if query_response is not None:
        return query_response

    logger.debug(
        "No study found in modality {} with UID '{}', trying MRN and accession number",
        modality,
        study.message.study_uid,
    )
    return await orthanc_raw.query_remote(
        study.orthanc_query_dict,
        modality=modality,
    )


def _is_daytime() -> bool:
    """Check if the current time is between 8 am and 8 pm."""
    timezone = ZoneInfo(config("TZ"))
    after_8am = datetime.time(8, 00) <= datetime.datetime.now(tz=timezone).time()
    before_8pm = datetime.datetime.now(tz=timezone).time() <= datetime.time(20, 00)
    return after_8am and before_8pm


def _is_weekend() -> bool:
    """Check if it's the weekend."""
    timezone = ZoneInfo(config("TZ"))
    saturday = 5
    sunday = 6
    return datetime.datetime.now(tz=timezone).weekday() in (saturday, sunday)


async def _retrieve_study(orthanc_raw: Orthanc, study_query_id: str) -> None:
    """Retrieve all instances for a study from the VNA / PACS."""
    job_id = await orthanc_raw.retrieve_study_from_remote(query_id=study_query_id)  # C-Move
    await orthanc_raw.wait_for_job_success_or_raise(
        job_id, "c-move", timeout=orthanc_raw.dicom_timeout
    )


async def _retrieve_missing_instances(
    resources: list[str],
    orthanc_raw: Orthanc,
    study: ImagingStudy,
    study_query_id: str,
    modality: str,
) -> None:
    """Retrieve missing instances for a study from the VNA / PACS."""
    missing_instance_uids = await _get_missing_instances(
        orthanc_raw=orthanc_raw, study=study, resources=resources, study_query_id=study_query_id
    )
    if not missing_instance_uids:
        return
    logger.debug(
        "Retrieving {} missing instances for study {}",
        len(missing_instance_uids),
        study.message.identifier,
    )
    job_id = await orthanc_raw.retrieve_instances_from_remote(modality, missing_instance_uids)
    await orthanc_raw.wait_for_job_success_or_raise(
        job_id, "c-move for missing instances", timeout=orthanc_raw.dicom_timeout
    )


async def _get_missing_instances(
    orthanc_raw: Orthanc, study: ImagingStudy, resources: list[str], study_query_id: str
) -> list[dict[str, str]]:
    """
    Check if any study instances are missing from Orthanc Raw.

    Return a list of missing instance UIDs (empty if none missing)
    """
    missing_instances: list[dict[str, str]] = []

    # First query the VNA / PACS for the study instances
    study_query_answers = await orthanc_raw.get_remote_query_answers(study_query_id)
    instances_queries_and_answers = []
    for answer_id in study_query_answers:
        instances_query_id = await orthanc_raw.get_remote_query_answer_instances(
            query_id=study_query_id, answer_id=answer_id
        )
        instances_query_answers = await orthanc_raw.get_remote_query_answers(instances_query_id)
        instances_queries_and_answers.extend(
            [(instances_query_id, answer) for answer in instances_query_answers]
        )
    num_remote_instances = len(instances_queries_and_answers)

    num_local_instances = 0
    for resource in resources:
        study_statistics = orthanc_raw.get_local_study_statistics(study_id=resource)
        num_local_instances += int(study_statistics["CountInstances"])

    if num_remote_instances == num_local_instances:
        logger.debug("No missing instances for study {}", study.message.study_uid)
        return missing_instances

    # Get all SOPInstanceUIDs for the study that are in Orthanc Raw
    orthanc_raw_sop_instance_uids = []
    for resource in resources:
        study_instances = await orthanc_raw.get_local_study_instances(study_id=resource)
        orthanc_raw_sop_instance_uids.extend(
            [instance["MainDicomTags"]["0008,0018"] for instance in study_instances]
        )

    # If the SOPInstanceUID is not in the list of instances in Orthanc Raw
    # retrieve the instance from the VNA / PACS
    query_tags = ["0020,000d", "0020,000e", "0008,0018"]
    for instances_query_id, instance_query_answer in instances_queries_and_answers:
        instance_query_answer_content = await orthanc_raw.get_remote_query_answer_content(
            query_id=instances_query_id,
            answer_id=instance_query_answer,
        )
        uids_for_query = {
            instance_query_answer_content[x]["Name"]: instance_query_answer_content[x]["Value"]
            for x in query_tags
        }
        sop_instance_uid = uids_for_query["SOPInstanceUID"]
        if sop_instance_uid in orthanc_raw_sop_instance_uids:
            continue

        logger.trace(
            "Instance {} is missing from study {}",
            sop_instance_uid,
            study.message.study_uid,
        )
        missing_instances.append(uids_for_query)

    return missing_instances


@dataclass
class ImagingStudy:
    """Dataclass for DICOM study unique to a patient and imaging study"""

    message: Message

    @classmethod
    def from_message(cls, message: Message) -> ImagingStudy:
        """Build an imaging study from a queue message."""
        return ImagingStudy(message=message)

    @property
    def orthanc_uid_query_dict(self) -> dict:
        """Build a dictionary to query a study with a study UID."""
        return {
            "Level": "Study",
            "Query": {
                "StudyInstanceUID": self.message.study_uid,
            },
        }

    @property
    def orthanc_query_dict(self) -> dict:
        """Build a dictionary to query a study on MRN and accession number."""
        return {
            "Level": "Study",
            "Query": {
                "PatientID": self.message.mrn,
                "AccessionNumber": self.message.accession_number,
            },
        }

    async def query_local(self, node: Orthanc) -> Any:
        """Does this study exist in an Orthanc instance/node."""
        if self.message.study_uid:
            uid_query = self.orthanc_uid_query_dict

            query_response = await node.query_local(uid_query)
            if query_response:
                return query_response

            logger.trace(
                "No study found locally with UID, trying MRN and accession number. {}",
                self.orthanc_query_dict,
            )
        else:
            logger.trace(
                "study_uid is empty, trying MRN and accession number. {}",
                self.orthanc_query_dict,
            )

        mrn_accession_query = self.orthanc_query_dict

        return await node.query_local(mrn_accession_query)
