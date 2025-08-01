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
import os
import pathlib
import shlex
from typing import TYPE_CHECKING

import pytest
from core.exceptions import PixlDiscardError, PixlOutOfHoursError, PixlStudyNotInPrimaryArchiveError
from core.patient_queue.message import Message
from decouple import config
from pydicom import dcmread
from pydicom.data import get_testdata_file
from pydicom.uid import generate_uid
from pytest_check import check
from pytest_pixl.helpers import run_subprocess

from pixl_imaging._orthanc import Orthanc, PIXLRawOrthanc
from pixl_imaging._processing import DicomModality, ImagingStudy, process_message

if TYPE_CHECKING:
    from collections.abc import Generator


pytest_plugins = ("pytest_asyncio",)

ACCESSION_NUMBER = "abc"
PATIENT_ID = "a_patient"
STUDY_UID = generate_uid(entropy_srcs=["12345678"])
SERIES_UID = generate_uid(entropy_srcs=["12345678.1"])
SERIES_UID_2 = generate_uid(entropy_srcs=["12345678.2"])
SOP_INSTANCE_UID = "1.1.1.1.1.1.1111.1.1.1.1.1.11111111111111.11111"
SOP_INSTANCE_UID_2 = "2.2.2.2.2.2.2222.2.2.2.2.2.22222222222222.22222"

PACS_ACCESSION_NUMBER = "def"
PACS_PATIENT_ID = "another_patient"
PACS_STUDY_UID = "87654321"

MISSING_ACCESSION_NUMBER = "ghi"
MISSING_PATIENT_ID = "missing_patient"
MISSING_STUDY_UID = "00000000"


@pytest.fixture(scope="module")
def message() -> Message:
    """A Message with a valid study_uid."""
    return Message(
        mrn=PATIENT_ID,
        accession_number=ACCESSION_NUMBER,
        study_uid=STUDY_UID,
        series_uid="",
        study_date=datetime.datetime.strptime("01/01/1234 01:23:45", "%d/%m/%Y %H:%M:%S").replace(
            tzinfo=datetime.UTC
        ),
        procedure_occurrence_id=234,
        project_name="test project",
        extract_generated_timestamp=datetime.datetime.fromisoformat("1234-01-01 00:00:00"),
    )


@pytest.fixture(scope="module")
def message_with_series_uids() -> Message:
    """A Message for querying a subset of series within a study."""
    return Message(
        mrn=PATIENT_ID,
        accession_number=ACCESSION_NUMBER,
        study_uid=STUDY_UID,
        series_uid=f"{SERIES_UID}\\{SERIES_UID_2}",
        study_date=datetime.datetime.strptime("01/01/1234 01:23:45", "%d/%m/%Y %H:%M:%S").replace(
            tzinfo=datetime.UTC
        ),
        procedure_occurrence_id=234,
        project_name="test project",
        extract_generated_timestamp=datetime.datetime.fromisoformat("1234-01-01 00:00:00"),
    )


@pytest.fixture(scope="module")
def message_with_single_series_uid() -> Message:
    """A Message for querying a subset of series within a study."""
    return Message(
        mrn=PATIENT_ID,
        accession_number=ACCESSION_NUMBER,
        study_uid=STUDY_UID,
        series_uid=f"{SERIES_UID}",
        study_date=datetime.datetime.strptime("01/01/1234 01:23:45", "%d/%m/%Y %H:%M:%S").replace(
            tzinfo=datetime.UTC
        ),
        procedure_occurrence_id=234,
        project_name="test project",
        extract_generated_timestamp=datetime.datetime.fromisoformat("1234-01-01 00:00:00"),
    )


@pytest.fixture(scope="module")
def no_uid_message() -> Message:
    """A Message with a valid study_uid."""
    return Message(
        mrn=PATIENT_ID,
        accession_number=ACCESSION_NUMBER,
        study_uid="",
        series_uid="",
        study_date=datetime.datetime.strptime("01/01/1234 01:23:45", "%d/%m/%Y %H:%M:%S").replace(
            tzinfo=datetime.UTC
        ),
        procedure_occurrence_id=234,
        project_name="test project",
        extract_generated_timestamp=datetime.datetime.fromisoformat("1234-01-01 00:00:00"),
    )


@pytest.fixture(scope="module")
def pacs_message() -> Message:
    """A Message with a valid study_uid for a study that exists in PACS but not VNA."""
    return Message(
        mrn=PACS_PATIENT_ID,
        accession_number=PACS_ACCESSION_NUMBER,
        study_uid=PACS_STUDY_UID,
        series_uid="",
        study_date=datetime.datetime.strptime("01/01/1234 01:23:45", "%d/%m/%Y %H:%M:%S").replace(
            tzinfo=datetime.UTC
        ),
        procedure_occurrence_id=234,
        project_name="test project",
        extract_generated_timestamp=datetime.datetime.fromisoformat("1234-01-01 00:00:00"),
    )


@pytest.fixture(scope="module")
def pacs_no_uid_message() -> Message:
    """A Message without a valid study_uid for a study that exists in PACS but not the VNA."""
    return Message(
        mrn=PACS_PATIENT_ID,
        accession_number=PACS_ACCESSION_NUMBER,
        study_uid="ialsodontexist",
        series_uid="",
        study_date=datetime.datetime.strptime("01/01/1234 01:23:45", "%d/%m/%Y %H:%M:%S").replace(
            tzinfo=datetime.UTC
        ),
        procedure_occurrence_id=234,
        project_name="test project",
        extract_generated_timestamp=datetime.datetime.fromisoformat("1234-01-01 00:00:00"),
    )


@pytest.fixture(scope="module")
def missing_message() -> Message:
    """A Message for a study that does not exist in PACS nor the VNA."""
    return Message(
        mrn=MISSING_PATIENT_ID,
        accession_number=MISSING_ACCESSION_NUMBER,
        study_uid=MISSING_STUDY_UID,
        series_uid="",
        study_date=datetime.datetime.strptime("01/01/1234 01:23:45", "%d/%m/%Y %H:%M:%S").replace(
            tzinfo=datetime.UTC
        ),
        procedure_occurrence_id=345,
        project_name="test project",
        extract_generated_timestamp=datetime.datetime.fromisoformat("1234-01-01 00:00:00"),
    )


class WritableOrthanc(Orthanc):
    def __init__(self, url: str, username: str, password: str, aet: str) -> None:
        super().__init__(
            url=url,
            username=username,
            password=password,
            http_timeout=config("PIXL_QUERY_TIMEOUT", cast=int),
            dicom_timeout=config("PIXL_DICOM_TRANSFER_TIMEOUT", cast=int),
            aet=aet,
        )

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
    vna = WritableOrthanc(
        aet="PRIMARYQR",
        url=config("ORTHANC_VNA_URL"),
        username=config("ORTHANC_VNA_USERNAME"),
        password=config("ORTHANC_VNA_PASSWORD"),
    )

    image_filename = "test.dcm"
    path = str(get_testdata_file("CT_small.dcm"))
    ds = dcmread(path)
    ds.AccessionNumber = ACCESSION_NUMBER
    ds.PatientID = PATIENT_ID
    ds.StudyInstanceUID = STUDY_UID
    ds.SeriesInstanceUID = SERIES_UID
    ds.SOPInstanceUID = SOP_INSTANCE_UID
    ds.save_as(image_filename)

    vna = WritableOrthanc(
        aet="PRIMARYQR",
        url=config("ORTHANC_VNA_URL"),
        username=config("ORTHANC_VNA_USERNAME"),
        password=config("ORTHANC_VNA_PASSWORD"),
    )
    vna.upload(image_filename)

    instance_2_image_filename = "test_2.dcm"
    ds.SeriesInstanceUID = SERIES_UID_2
    ds.SOPInstanceUID = SOP_INSTANCE_UID_2
    ds.save_as(instance_2_image_filename)
    vna.upload(instance_2_image_filename)

    yield
    pathlib.Path(image_filename).unlink(missing_ok=True)
    pathlib.Path(instance_2_image_filename).unlink(missing_ok=True)


@pytest.fixture(scope="module")
def _add_image_to_fake_pacs(run_containers) -> Generator[None]:
    """Add single fake image to PACS."""
    image_filename = "test-mr.dcm"
    path = str(get_testdata_file("MR_small.dcm"))
    ds = dcmread(path)
    ds.AccessionNumber = PACS_ACCESSION_NUMBER
    ds.PatientID = PACS_PATIENT_ID
    ds.StudyInstanceUID = PACS_STUDY_UID
    ds.save_as(image_filename)

    pacs = WritableOrthanc(
        aet="SECONDARYQR",
        url=config("ORTHANC_PACS_URL"),
        username=config("ORTHANC_PACS_USERNAME"),
        password=config("ORTHANC_PACS_PASSWORD"),
    )
    pacs.upload(image_filename)
    yield
    pathlib.Path(image_filename).unlink(missing_ok=True)


@pytest.fixture
async def orthanc_raw(run_containers) -> PIXLRawOrthanc:
    """Set up orthanc raw and remove all studies in teardown."""
    orthanc_raw = PIXLRawOrthanc()
    try:
        return orthanc_raw
    finally:
        all_studies = await orthanc_raw._get("/studies")
        for study in all_studies:
            await orthanc_raw.delete(f"/studies/{study}")


@pytest.mark.processing
@pytest.mark.asyncio
@pytest.mark.usefixtures("_add_image_to_fake_vna")
async def test_image_saved(orthanc_raw, message: Message) -> None:
    """
    Given the VNA has images, and orthanc raw has no images
    When we run process_message
    Then orthanc raw will contain the new image
    """
    study = ImagingStudy.from_message(message)

    orthanc = await orthanc_raw

    assert not await study.query_local(orthanc, query_level=study.query_level)
    await process_message(message, archive=DicomModality.primary)

    studies = await study.query_local(orthanc, query_level=study.query_level)
    assert len(studies) == 1

    study_info = await orthanc._get(f"/studies/{studies[0]}")
    with check:
        assert study_info["MainDicomTags"]["AccessionNumber"] == ACCESSION_NUMBER
        assert study_info["PatientMainDicomTags"]["PatientID"] == PATIENT_ID
        assert study_info["MainDicomTags"]["StudyInstanceUID"] == STUDY_UID

    series_info = await orthanc._get(f"/series/{study_info['Series'][0]}")
    with check:
        assert series_info["MainDicomTags"]["SeriesInstanceUID"] in (
            SERIES_UID,
            SERIES_UID_2,
        )

    instance_info = await orthanc._get(f"/instances/{series_info['Instances'][0]}")
    with check:
        assert instance_info["MainDicomTags"]["SOPInstanceUID"] in (
            SOP_INSTANCE_UID,
            SOP_INSTANCE_UID_2,
        )


@pytest.mark.processing
@pytest.mark.asyncio
@pytest.mark.usefixtures("_add_image_to_fake_vna")
async def test_message_with_series_uids(
    orthanc_raw, message_with_series_uids: Message, caplog
) -> None:
    """
    Given the VNA has a single study with 2 series, and Orthanc Raw has no images
    When we run process_message
    Then Orthanc Raw will contain both series from the study.
    """
    study = ImagingStudy.from_message(message_with_series_uids)
    orthanc = await orthanc_raw

    assert not await study.query_local(orthanc, query_level="Study")
    await process_message(message_with_series_uids, archive=DicomModality.primary)

    studies = await study.query_local(orthanc, query_level="Study")
    assert len(studies) == 1

    study_info = await orthanc._get(f"/studies/{studies[0]}")
    with check:
        assert study_info["MainDicomTags"]["AccessionNumber"] == ACCESSION_NUMBER
        assert study_info["PatientMainDicomTags"]["PatientID"] == PATIENT_ID
        assert study_info["MainDicomTags"]["StudyInstanceUID"] == STUDY_UID

    assert len(study_info["Series"]) == 2

    for series in study_info["Series"]:
        series_info = await orthanc._get(f"/series/{series}")
        with check:
            assert series_info["MainDicomTags"]["SeriesInstanceUID"] in (
                SERIES_UID,
                SERIES_UID_2,
            )


@pytest.mark.processing
@pytest.mark.asyncio
@pytest.mark.usefixtures("_add_image_to_fake_vna")
async def test_message_with_one_series_uid(
    orthanc_raw, message_with_single_series_uid: Message, caplog
) -> None:
    """
    Given the VNA has a single study with 2 series, and Orthanc Raw has no images
    When we run process_message
    Then Orthanc Raw will contain only the series included in the message.
    """
    study = ImagingStudy.from_message(message_with_single_series_uid)
    orthanc = await orthanc_raw

    assert not await study.query_local(orthanc, query_level="Study")
    await process_message(message_with_single_series_uid, archive=DicomModality.primary)

    studies = await study.query_local(orthanc, query_level="Study")
    assert len(studies) == 1

    study_info = await orthanc._get(f"/studies/{studies[0]}")
    with check:
        assert study_info["MainDicomTags"]["AccessionNumber"] == ACCESSION_NUMBER
        assert study_info["PatientMainDicomTags"]["PatientID"] == PATIENT_ID
        assert study_info["MainDicomTags"]["StudyInstanceUID"] == STUDY_UID

    assert len(study_info["Series"]) == 1

    series_info = await orthanc._get(f"/series/{study_info['Series'][0]}")
    with check:
        assert series_info["MainDicomTags"]["SeriesInstanceUID"] == SERIES_UID


@pytest.mark.processing
@pytest.mark.asyncio
@pytest.mark.usefixtures("_add_image_to_fake_vna")
async def test_partial_retrieve(orthanc_raw, message: Message, caplog) -> None:
    """
    Given the VNA has a single study with 2 instances, and orthanc raw has the same study with
    1 instance
    When we run process_message
    Then orthanc raw will contain both instances after retrieving only the missing instance
    """
    study = ImagingStudy.from_message(message)

    orthanc = await orthanc_raw

    assert not await study.query_local(orthanc, query_level=study.query_level)
    await process_message(message, archive=DicomModality.primary)
    assert await study.query_local(orthanc, query_level=study.query_level)

    all_instances = await orthanc._get("/instances")
    assert len(all_instances) == 2

    instance_info = {}

    with check:
        for instance in all_instances:
            instance_info = await orthanc._get(f"/instances/{instance}")
            sop_instance_uid = instance_info["MainDicomTags"]["SOPInstanceUID"]
            assert sop_instance_uid in (SOP_INSTANCE_UID, SOP_INSTANCE_UID_2)

    await orthanc.delete(f"/instances/{instance_info['ID']}")

    await process_message(message, archive=DicomModality.primary)
    all_instances = await orthanc._get("/instances")
    assert len(all_instances) == 2

    expected_msg = (
        f"Instance {instance_info['MainDicomTags']['SOPInstanceUID']}"
        f" is missing from study {STUDY_UID}"
    )
    assert expected_msg in caplog.text


@pytest.mark.processing
@pytest.mark.asyncio
@pytest.mark.usefixtures("_add_image_to_fake_vna")
async def test_existing_message_sent_twice(orthanc_raw, message: Message) -> None:
    """
    Given the VNA has images, and orthanc raw has no images
    When we run process_message on the same message twice
    Then orthanc raw will contain the new image, and it isn't updated on the second processing
    """
    study = ImagingStudy.from_message(message)
    orthanc = await orthanc_raw

    await process_message(message, archive=DicomModality.primary)
    assert await study.query_local(orthanc, query_level=study.query_level)

    query_for_update_time = {**study.orthanc_query_dict, "Expand": True}
    first_processing_resource = await orthanc.query_local(query_for_update_time)
    assert len(first_processing_resource) == 1

    await process_message(message, archive=DicomModality.primary)
    second_processing_resource = await orthanc.query_local(query_for_update_time)
    assert len(second_processing_resource) == 1

    # Check update time hasn't changed
    assert first_processing_resource[0]["LastUpdate"] == second_processing_resource[0]["LastUpdate"]

    studies = await study.query_local(orthanc, query_level=study.query_level)
    assert len(studies) == 1

    study_info = await orthanc._get(f"/studies/{studies[0]}")
    with check:
        assert study_info["MainDicomTags"]["AccessionNumber"] == ACCESSION_NUMBER
        assert study_info["PatientMainDicomTags"]["PatientID"] == PATIENT_ID
        assert study_info["MainDicomTags"]["StudyInstanceUID"] == STUDY_UID

    series_info = await orthanc._get(f"/series/{study_info['Series'][0]}")
    with check:
        assert series_info["MainDicomTags"]["SeriesInstanceUID"] in (
            SERIES_UID,
            SERIES_UID_2,
        )

    instance_info = await orthanc._get(f"/instances/{series_info['Instances'][0]}")
    with check:
        assert instance_info["MainDicomTags"]["SOPInstanceUID"] in (
            SOP_INSTANCE_UID,
            SOP_INSTANCE_UID_2,
        )


@pytest.mark.processing
@pytest.mark.asyncio
@pytest.mark.usefixtures("_add_image_to_fake_vna")
async def test_querying_without_uid(orthanc_raw, caplog, no_uid_message: Message) -> None:
    """
    Given a message with non-existent study_uid
    When we query the VNA
    Then the querying falls back to using the MRN and accession number
    """
    study = ImagingStudy.from_message(no_uid_message)
    orthanc = await orthanc_raw

    assert not await study.query_local(orthanc, query_level=study.query_level)
    await process_message(no_uid_message, archive=DicomModality.primary)
    assert await study.query_local(orthanc, query_level=study.query_level)

    expected_msg = (
        f"No study found in modality UCPRIMARYQR with UID '{study.message.study_uid}', "
        "trying MRN and accession number"
    )
    assert expected_msg in caplog.text


class Monday2AM(datetime.datetime):
    @classmethod
    def now(cls, tz=None) -> datetime.datetime:
        return cls(2024, 1, 1, 2, 0, tzinfo=tz)


class Monday11AM(datetime.datetime):
    @classmethod
    def now(cls, tz=None) -> datetime.datetime:
        return cls(2024, 1, 1, 11, 0, tzinfo=tz)


class Saturday2AM(datetime.datetime):
    @classmethod
    def now(cls, tz=None) -> datetime.datetime:
        return datetime.datetime(2024, 1, 6, 2, 0, tzinfo=tz)


@pytest.mark.processing
@pytest.mark.asyncio
@pytest.mark.usefixtures("_add_image_to_fake_pacs")
async def test_querying_pacs_with_uid(
    orthanc_raw, caplog, monkeypatch, pacs_message: Message
) -> None:
    """
    Given a message with study_uid exists in PACS but not VNA,
    When we query the archives
    Then the querying finds the study in PACS with the study_uid
    """
    study = ImagingStudy.from_message(pacs_message)
    orthanc = await orthanc_raw

    assert not await study.query_local(orthanc, query_level=study.query_level)

    # PACS is not queried during the daytime nor at the weekend.
    # Set today to be a Monday at 2 am.
    with monkeypatch.context() as mp:
        mp.setattr(datetime, "datetime", Monday2AM)
        match = "sending message to secondary imaging queue."
        with pytest.raises(PixlStudyNotInPrimaryArchiveError, match=match):
            await process_message(pacs_message, archive=DicomModality.primary)
        await process_message(pacs_message, archive=DicomModality.secondary)

    assert await study.query_local(orthanc, query_level=study.query_level)

    expected_msg = (
        f"No study found in modality UCPRIMARYQR with UID '{study.message.study_uid}', "
        "trying MRN and accession number"
    )
    assert expected_msg in caplog.text

    unexpected_msg = (
        f"No study found in modality UCSECONDARYQR with UID '{study.message.study_uid}', "
        "trying MRN and accession number"
    )
    assert unexpected_msg not in caplog.text


@pytest.mark.processing
@pytest.mark.asyncio
@pytest.mark.usefixtures("_add_image_to_fake_pacs")
async def test_querying_pacs_without_uid(
    orthanc_raw, caplog, monkeypatch, pacs_no_uid_message: Message
) -> None:
    """
    Given a message with non-existent study_uid exists in PACS but not VNA,
    When we query the archives
    Then the querying falls back to using the MRN and accession number and finds the study in PACS
    """
    study = ImagingStudy.from_message(pacs_no_uid_message)
    orthanc = await orthanc_raw

    assert not await study.query_local(orthanc, query_level=study.query_level)

    # PACS is not queried during the daytime nor at the weekend.
    # Set today to be a Monday at 2 am.
    with monkeypatch.context() as mp:
        mp.setattr(datetime, "datetime", Monday2AM)
        match = "sending message to secondary imaging queue."
        with pytest.raises(PixlStudyNotInPrimaryArchiveError, match=match):
            await process_message(pacs_no_uid_message, archive=DicomModality.primary)
        await process_message(pacs_no_uid_message, archive=DicomModality.secondary)

    assert await study.query_local(orthanc, query_level=study.query_level)

    expected_msg = "No study found in modality UCPRIMARYQR with UID"
    assert expected_msg in caplog.text

    expected_msg = (
        f"No study found in modality UCSECONDARYQR with UID '{study.message.study_uid}', "
        "trying MRN and accession number"
    )
    assert expected_msg in caplog.text


@pytest.mark.processing
@pytest.mark.asyncio
async def test_querying_missing_image(orthanc_raw, monkeypatch, missing_message: Message) -> None:
    """
    Given a message for a study that is missing in both the VNA and PACS,
    When we query the archives within the window of Monday-Friday 8pm to 8am,
    Then the querying tries both the VNA and PACS and raises a PixlDiscardError
    """
    study = ImagingStudy.from_message(missing_message)
    orthanc = await orthanc_raw

    assert not await study.query_local(orthanc, query_level=study.query_level)

    # PACS is not queried during the daytime nor at the weekend.
    # Set today to be a Monday at 2 am.
    primary_match = "sending message to secondary imaging queue."
    secondary_match = "Failed to find study .* in primary or secondary archive."
    with (  # noqa: PT012
        monkeypatch.context() as mp,
        pytest.raises(PixlStudyNotInPrimaryArchiveError, match=primary_match),
        pytest.raises(PixlDiscardError, match=secondary_match),
    ):
        mp.setattr(datetime, "datetime", Monday2AM)
        await process_message(missing_message, archive=DicomModality.primary)
        await process_message(missing_message, archive=DicomModality.secondary)


@pytest.mark.processing
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query_date",
    [
        (Monday11AM),
        (Saturday2AM),
    ],
)
async def test_querying_pacs_during_working_hours(
    orthanc_raw, query_date, monkeypatch, missing_message: Message
) -> None:
    """
    Given a message for a study that is missing in both the VNA and PACS,
    When we query the archives outside of Monday-Friday 8pm-8am,
    Then the querying tries only the VNA and raises a PixlDiscardError
    """
    study = ImagingStudy.from_message(missing_message)
    orthanc = await orthanc_raw

    assert not await study.query_local(orthanc, query_level=study.query_level)

    match = "Not querying secondary archive during the daytime or on the weekend."
    with monkeypatch.context() as mp, pytest.raises(PixlOutOfHoursError, match=match):  # noqa: PT012
        mp.setattr(datetime, "datetime", query_date)
        await process_message(missing_message, archive=DicomModality.secondary)


@pytest.mark.processing
@pytest.mark.asyncio
async def test_querying_pacs_not_defined(
    orthanc_raw, monkeypatch, missing_message: Message
) -> None:
    """
    Given a message for a study that is missing in the VNA and the SECONDARY_DICOM_SOURCE_AE_TITLE
    is the same as the PRIMARY_DICOM_SOURCE_AE_TITLE
    When we query the archive,
    Then the querying tries the VNA and then raises a PixlDiscardError
    """
    study = ImagingStudy.from_message(missing_message)
    orthanc = await orthanc_raw

    assert not await study.query_local(orthanc, query_level=study.query_level)

    match = (
        "Failed to find study .* in primary archive "
        "and SECONDARY_DICOM_SOURCE_AE_TITLE is the same as PRIMARY_DICOM_SOURCE_AE_TITLE."
    )
    with (  # noqa: PT012
        monkeypatch.context() as mp,
        pytest.raises(PixlDiscardError, match=match),
    ):
        mp.setenv("SECONDARY_DICOM_SOURCE_AE_TITLE", os.environ["PRIMARY_DICOM_SOURCE_AE_TITLE"])
        await process_message(missing_message, archive=DicomModality.primary)
