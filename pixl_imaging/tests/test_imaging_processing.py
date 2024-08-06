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
"""These tests require docker containers to be up to be able to run."""

from __future__ import annotations

import datetime
import pathlib
import shlex
from typing import TYPE_CHECKING

import pytest
from core.patient_queue.message import Message
from decouple import config
from pixl_imaging._orthanc import Orthanc, PIXLRawOrthanc
from pixl_imaging._processing import ImagingStudy, process_message
from pydicom import dcmread
from pydicom.data import get_testdata_file
from pytest_pixl.helpers import run_subprocess

if TYPE_CHECKING:
    from collections.abc import Generator


pytest_plugins = ("pytest_asyncio",)

ACCESSION_NUMBER = "abc"
PATIENT_ID = "a_patient"
STUDY_UID = "12345678"
message = Message(
    mrn=PATIENT_ID,
    accession_number=ACCESSION_NUMBER,
    study_uid=STUDY_UID,
    study_date=datetime.datetime.strptime("01/01/1234 01:23:45", "%d/%m/%Y %H:%M:%S").replace(
        tzinfo=datetime.timezone.utc
    ),
    procedure_occurrence_id=234,
    project_name="test project",
    extract_generated_timestamp=datetime.datetime.fromisoformat("1234-01-01 00:00:00"),
)
no_uid_message = Message(
    mrn=PATIENT_ID,
    accession_number=ACCESSION_NUMBER,
    study_uid="idontexist",
    study_date=datetime.datetime.strptime("01/01/1234 01:23:45", "%d/%m/%Y %H:%M:%S").replace(
        tzinfo=datetime.timezone.utc
    ),
    procedure_occurrence_id=234,
    project_name="test project",
    extract_generated_timestamp=datetime.datetime.fromisoformat("1234-01-01 00:00:00"),
)


class WritableOrthanc(Orthanc):
    @property
    def aet(self) -> str:
        return "VNAQR"

    def upload(self, filename: str) -> None:
        run_subprocess(
            shlex.split(
                f"curl -u {self._username}:{self._password} "
                f"-X POST {self._url}/instances --data-binary @{filename}"
            )
        )


@pytest.fixture(scope="module")
def _add_image_to_fake_vna(run_containers) -> Generator[None]:
    """Add single fake image to VNA."""
    image_filename = "test.dcm"
    path = str(get_testdata_file("CT_small.dcm"))
    ds = dcmread(path)
    ds.AccessionNumber = ACCESSION_NUMBER
    ds.PatientID = PATIENT_ID
    ds.StudyInstanceUID = STUDY_UID
    ds.save_as(image_filename)

    vna = WritableOrthanc(
        url=config("ORTHANC_VNA_URL"),
        username=config("ORTHANC_VNA_USERNAME"),
        password=config("ORTHANC_VNA_PASSWORD"),
    )
    vna.upload(image_filename)
    yield
    pathlib.Path(image_filename).unlink(missing_ok=True)


@pytest.fixture()
async def orthanc_raw(run_containers) -> PIXLRawOrthanc:
    """Set up orthanc raw and remove all studies in teardown."""
    orthanc_raw = PIXLRawOrthanc()
    try:
        return orthanc_raw
    finally:
        all_studies = await orthanc_raw._get("/studies")
        for study in all_studies:
            await orthanc_raw.delete(f"/studies/{study}")


@pytest.mark.processing()
@pytest.mark.asyncio()
@pytest.mark.usefixtures("_add_image_to_fake_vna")
async def test_image_saved(orthanc_raw) -> None:
    """
    Given the VNA has images, and orthanc raw has no images
    When we run process_message
    Then orthanc raw will contain the new image
    """
    study = ImagingStudy.from_message(message)

    orthanc = await orthanc_raw

    assert not await study.query_local(orthanc)
    await process_message(message)
    assert await study.query_local(orthanc)


@pytest.mark.processing()
@pytest.mark.asyncio()
@pytest.mark.usefixtures("_add_image_to_fake_vna")
async def test_existing_message_sent_twice(orthanc_raw) -> None:
    """
    Given the VNA has images, and orthanc raw has no images
    When we run process_message on the same message twice
    Then orthanc raw will contain the new image, and it isn't updated on the second processing
    """
    study = ImagingStudy.from_message(message)
    orthanc = await orthanc_raw

    await process_message(message)
    assert await study.query_local(orthanc)

    query_for_update_time = {**study.orthanc_query_dict, "Expand": True}
    first_processing_resource = await orthanc.query_local(query_for_update_time)
    assert len(first_processing_resource) == 1

    await process_message(message)
    second_processing_resource = await orthanc.query_local(query_for_update_time)
    assert len(second_processing_resource) == 1

    # Check update time hasn't changed
    assert first_processing_resource[0]["LastUpdate"] == second_processing_resource[0]["LastUpdate"]


@pytest.mark.processing()
@pytest.mark.asyncio()
@pytest.mark.usefixtures("_add_image_to_fake_vna")
async def test_querying_without_uid(orthanc_raw, caplog) -> None:
    """
    Given a message with non-existent study_uid
    When we query the VNA
    Then the querying falls back to using the MRN and accession number
    """
    study = ImagingStudy.from_message(no_uid_message)
    orthanc = await orthanc_raw

    assert not await study.query_local(orthanc)
    await process_message(no_uid_message)
    assert await study.query_local(orthanc)

    expected_msg = (
        f"No study found with UID {study.message.study_uid}, trying MRN and accession number"
    )
    assert expected_msg in caplog.text
