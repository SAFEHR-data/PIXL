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
These tests require executing from within the EHR API container with the dependent
services being up
    - pixl postgres db
    - emap star
"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime
from logging import getLogger
from typing import Any, Optional

import pytest
from core.exports import ParquetExport
from core.patient_queue.message import Message
from decouple import config
from pixl_ehr._databases import PIXLDatabase, WriteableDatabase
from pixl_ehr._processing import process_message
from psycopg2.errors import UniqueViolation

pytest_plugins = ("pytest_asyncio",)

logger = getLogger(__name__)


@dataclasses.dataclass
class MockResponse:
    """Mock response object for get or post."""

    status_code = 200
    content: str | None
    text: str | None


@pytest.fixture(autouse=True)
def _mock_requests(monkeypatch) -> None:
    """Mock requests so we don't have to run APIs."""

    def mock_get(url: str, params: dict, *args: Any, **kwargs: Any) -> MockResponse:
        logger.info("Mocking request for %s: %s", url, params)
        return MockResponse(
            content="-".join(list(params["message"])), text="-".join(list(params["message"]))
        )

    def mock_post(url: str, data, *args: Any, **kwargs: Any) -> MockResponse:
        logger.info("Mocking request for %s: %s", url, data)
        return MockResponse(content=data + "**DE-IDENTIFIED**", text=data + "**DE-IDENTIFIED**")

    monkeypatch.setattr("requests.get", mock_get)
    monkeypatch.setattr("requests.post", mock_post)


@pytest.fixture(autouse=True)
def _pixl_db() -> None:
    pixl_db = QueryablePIXLDB()
    pixl_db.execute_and_commit("delete from emap_data.ehr_raw")
    pixl_db.execute_and_commit("delete from emap_data.ehr_anon")


mrn = "testmrn"

accession_number_base = "testaccessionnumber"


def _test_accession_number(acc_id: int) -> str:
    return f"{accession_number_base}{acc_id}"


observation_datetime = datetime.datetime.fromisoformat("2024-01-01")
procedure_occurrence_id = 123456
image_identifier = mrn + _test_accession_number(1)
project_name_1 = "test project"
project_name_2 = "other project"
extract_generated_timestamp_1 = datetime.datetime.fromisoformat("1234-01-01 00:00:00")
extract_generated_timestamp_2 = datetime.datetime.fromisoformat("1834-01-01 00:00:00")
date_of_birth = "09/08/0007"
sex = "testsexvalue"
ethnicity = "testethnicity"
height = 123.0
weight = 45.0
gcs = 6
name_of_doctor = "John Smith"
report_text = f"test\nxray report\nsigned by {name_of_doctor}"

procedure_occurrence_id2 = 234567
image_identifier2 = mrn + _test_accession_number(2)
report_text2 = "test\nanother xray report\nsigned by someone else"

# Primary/foreign keys used to insert linked mrns, hospital visits, labs
# visit observation types
mrn_id = 9999999
hv_id = 1111111
weight_vot_id, height_vot_id, gcs_vot_id = 2222222, 3333333, 4444444
ls_id, lo_id, lr_id, ltd_id = 5555555, 6666666, 7777777, 8888888


def _make_message(project_name, extract_generated_timestamp, accession_number) -> Message:
    slugified_project_name, _ = ParquetExport._get_slugs(project_name, extract_generated_timestamp)  # noqa: SLF001
    return Message(
        project_name=slugified_project_name,
        accession_number=accession_number,
        mrn=mrn,
        study_date=observation_datetime,
        procedure_occurrence_id=procedure_occurrence_id,
        extract_generated_timestamp=extract_generated_timestamp,
    )


@pytest.fixture()
def example_messages():
    """Test input data."""
    return [
        _make_message(
            project_name=project_name_1,
            extract_generated_timestamp=extract_generated_timestamp_1,
            accession_number=_test_accession_number(1),
        ),
        _make_message(
            project_name=project_name_2,
            extract_generated_timestamp=extract_generated_timestamp_1,
            accession_number=_test_accession_number(2),
        ),
        _make_message(
            project_name=project_name_1,
            extract_generated_timestamp=extract_generated_timestamp_2,
            accession_number=_test_accession_number(3),
        ),
        _make_message(
            project_name=project_name_2,
            extract_generated_timestamp=extract_generated_timestamp_2,
            accession_number=_test_accession_number(4),
        ),
    ]


class WritableEMAPStar(WriteableDatabase):
    def __init__(self) -> None:
        super().__init__(
            db_name=config("EMAP_UDS_NAME"),
            username=config("EMAP_UDS_USER"),
            password=config("EMAP_UDS_PASSWORD"),
            host=config("EMAP_UDS_HOST"),
            port=config("EMAP_UDS_PORT", int),
        )

        if config("EMAP_UDS_HOST") not in ("star", "localhost"):
            msg = (
                "It looks like the host was not a docker-compose "
                "created service. Cannot create a writable EMAPStar"
            )
            raise RuntimeError(msg)


class QueryablePIXLDB(PIXLDatabase):
    def execute_query_string(self, query: str, values: Optional[list] = None) -> tuple:
        self._cursor.execute(query=query, vars=values)
        return self._cursor.fetchall()

    def execute_and_commit(self, query: str):
        self._cursor.execute(query=query, vars=[])
        self._connection.commit()


def insert_row_into_emap_star_schema(table_name: str, col_names: list[str], values: list) -> None:
    db = WritableEMAPStar()
    cols = ",".join(col_names)
    vals = ",".join("%s" for _ in range(len(col_names)))

    with contextlib.suppress(UniqueViolation):
        db.persist(
            f"INSERT INTO star.{table_name} ({cols}) VALUES ({vals})",
            values,
        )  # If it's already there then all is okay, hopefully


def insert_data_into_emap_star_schema() -> None:
    insert_row_into_emap_star_schema("mrn", ["mrn_id", "mrn"], [mrn_id, mrn])
    insert_row_into_emap_star_schema(
        "core_demographic",
        ["mrn_id", "date_of_birth", "sex", "ethnicity"],
        [mrn_id, date_of_birth, sex, ethnicity],
    )
    insert_row_into_emap_star_schema(
        "hospital_visit", ["hospital_visit_id", "mrn_id"], [hv_id, mrn_id]
    )

    # First message data
    insert_row_into_emap_star_schema(
        "lab_sample",
        ["lab_sample_id", "external_lab_number", "mrn_id"],
        [ls_id, _test_accession_number(1), mrn_id],
    )
    # Second message data
    insert_row_into_emap_star_schema(
        "lab_sample",
        ["lab_sample_id", "external_lab_number", "mrn_id"],
        [ls_id, _test_accession_number(2), mrn_id],
    )
    insert_row_into_emap_star_schema("lab_order", ["lab_order_id", "lab_sample_id"], [lo_id, ls_id])
    insert_row_into_emap_star_schema(
        "lab_test_definition",
        ["lab_test_definition_id", "test_lab_code"],
        [ltd_id, "NARRATIVE"],
    )
    # First message radiology report
    insert_row_into_emap_star_schema(
        "lab_result",
        ["lab_result_id", "lab_order_id", "lab_test_definition_id", "value_as_text"],
        [lr_id, lo_id, ltd_id, report_text],
    )
    # Second message radiology report
    insert_row_into_emap_star_schema(
        "lab_result",
        ["lab_result_id", "lab_order_id", "lab_test_definition_id", "value_as_text"],
        [lr_id, lo_id, ltd_id, report_text2],
    )


@pytest.mark.processing()
@pytest.mark.asyncio()
@pytest.mark.usefixtures("run_containers")
async def test_message_processing(example_messages) -> None:
    """
    GIVEN some patient metadata in Emap
    WHEN a message is processed requesting EHR data from Emap
    THEN The row of data is added to the PIXL DB
    """
    ## ARRANGE
    insert_data_into_emap_star_schema()

    message = example_messages[0]

    expected_row = [
        mrn,
        message.accession_number,
        image_identifier,
        procedure_occurrence_id,
        report_text,
        message.project_name,
        message.extract_generated_timestamp,
    ]
    ## ACT
    await process_message(message)

    ## ASSERT
    pixl_db = QueryablePIXLDB()

    # Check that an EHR was added to the PIXL DB
    select_columns = [
        "mrn",
        "accession_number",
        "image_identifier",
        "procedure_occurrence_id",
        "xray_report",
        "project_name",
        "extract_datetime",
    ]
    all_rows = pixl_db.execute_query_string(
        f"select {', '.join(select_columns)} from emap_data.ehr_raw where mrn = %s",
        [mrn],
    )
    assert len(all_rows) == 1
    row = all_rows[0]

    for value, expected_value in zip(row, expected_row, strict=True):
        assert value == expected_value

    # Check that anonymised EHR was added to the PIXL DB
    anon_all_rows = pixl_db.execute_query_string(
        "select mrn, accession_number, xray_report from "
        "emap_data.ehr_anon where procedure_occurrence_id = %s",
        [procedure_occurrence_id],
    )
    assert len(anon_all_rows) == 1
    anon_row = anon_all_rows[0]
    anon_mrn, anon_accession_number, anon_report_text = anon_row
    assert anon_mrn != mrn
    assert anon_accession_number != message.accession_number

    # Check that CogStack de-identification was called
    assert anon_report_text == report_text + "**DE-IDENTIFIED**"
