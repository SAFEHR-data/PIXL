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
"""
These tests require executing from within the PACS API container with the dependent
services being up
"""
import datetime
import os

import pytest
from core.patient_queue import Message
from decouple import config
from pixl_pacs._orthanc import Orthanc, PIXLRawOrthanc
from pixl_pacs._processing import ImagingStudy, process_message
from pydicom import dcmread
from pydicom.data import get_testdata_file

pytest_plugins = ("pytest_asyncio",)

ACCESSION_NUMBER = "abc"
PATIENT_ID = "a_patient"
message = Message(
    {
        "mrn": PATIENT_ID,
        "accession_number": ACCESSION_NUMBER,
        "study_datetime": datetime.datetime.strptime(
            "01/01/1234 01:23:45", "%d/%m/%Y %H:%M:%S"
        ).replace(tzinfo=datetime.timezone.utc),
        "procedure_occurrence_id": "234",
        "project_name": "test project",
        "omop_es_timestamp": datetime.datetime.fromisoformat("1234-01-01 00:00:00"),
    }
)
serialised_message = message.serialise()


class WritableOrthanc(Orthanc):
    @property
    def aet(self) -> str:
        return "VNAQR"

    def upload(self, filename: str) -> None:
        os.system(
            f"curl -u {self._username}:{self._password} "  # noqa: S605
            f"-X POST {self._url}/instances --data-binary @{filename}"
        )


def add_image_to_fake_vna(image_filename: str = "test.dcm") -> None:
    path = get_testdata_file("CT_small.dcm")
    ds = dcmread(path)
    ds.AccessionNumber = ACCESSION_NUMBER
    ds.PatientID = PATIENT_ID
    ds.save_as(image_filename)

    vna = WritableOrthanc(
        url="http://vna-qr:8042",
        username=config("ORTHANC_VNA_USERNAME"),
        password=config("ORTHANC_VNA_PASSWORD"),
    )
    vna.upload(image_filename)


@pytest.mark.processing()
@pytest.mark.asyncio()
async def test_image_processing() -> None:
    add_image_to_fake_vna()
    study = ImagingStudy.from_message(serialised_message)
    orthanc_raw = PIXLRawOrthanc()

    assert not study.exists_in(orthanc_raw)
    await process_message(serialised_message)
    assert study.exists_in(orthanc_raw)

    # TODO: check time last updated after processing again # noqa: FIX002
    # is not incremented
    # https://github.com/UCLH-Foundry/PIXL/issues/156
    await process_message(serialised_message)
    assert study.exists_in(orthanc_raw)
