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
import contextlib
import datetime

import pytest
from core.patient_queue.utils import serialise
from decouple import config
from pixl_ehr._databases import PIXLDatabase, WriteableDatabase
from pixl_ehr._processing import process_message
from psycopg2.errors import UniqueViolation

pytest_plugins = ("pytest_asyncio",)


mrn = "testmrn"
accession_number = "testaccessionnumber"
study_datetime_str = "01/01/1234 01:23"
observation_datetime = datetime.datetime.fromisoformat(
    "1234-01-01"
)  # within hours of imaging study
date_of_birth = "09/08/0007"
sex = "testsexvalue"
ethnicity = "testethnicity"
height = 123.0
weight = 45.0
gcs = 6
name_of_doctor = "John Smith"
report_text = f"test\nxray report\nsigned by {name_of_doctor}"

# Primary/foreign keys used to insert linked mrns, hospital visits, labs
# visit observation types
mrn_id = 9999999
hv_id = 1111111
weight_vot_id, height_vot_id, gcs_vot_id = 2222222, 3333333, 4444444
ls_id, lo_id, lr_id, ltd_id = 5555555, 6666666, 7777777, 8888888

message_body = serialise(
    mrn=mrn,
    accession_number=accession_number,
    study_datetime=datetime.datetime.strptime(
        study_datetime_str, "%d/%m/%Y %H:%M"
    ).replace(tzinfo=datetime.timezone.utc),
)


class WritableEMAPStar(WriteableDatabase):
    def __init__(self) -> None:
        super().__init__(
            db_name=config("EMAP_UDS_NAME"),
            username=config("EMAP_UDS_USER"),
            password=config("EMAP_UDS_PASSWORD"),
            host=config("EMAP_UDS_HOST"),
        )

        if config("EMAP_UDS_HOST") != "star":
            msg = (
                "It looks like the host was not a docker-compose "
                "created service. Cannot create a writable EMAPStar"
            )
            raise RuntimeError(msg)


class QueryablePIXLDB(PIXLDatabase):
    def execute_query_string(self, query: str, values: list) -> tuple:
        self._cursor.execute(query=query, vars=values)
        row = self._cursor.fetchone()
        return tuple(row)


def insert_row_into_emap_star_schema(
    table_name: str, col_names: list[str], values: list
) -> None:
    db = WritableEMAPStar()
    cols = ",".join(col_names)
    vals = ",".join("%s" for _ in range(len(col_names)))

    with contextlib.suppress(UniqueViolation):
        db.persist(
            f"INSERT INTO star.{table_name} ({cols}) VALUES ({vals})",
            values,
        )  # If it's already there then all is okay, hopefully


def insert_visit_observation(type_id: int, value: float) -> None:
    insert_row_into_emap_star_schema(
        "visit_observation",
        [
            "hospital_visit_id",
            "visit_observation_type_id",
            "value_as_real",
            "observation_datetime",
        ],
        [hv_id, type_id, value, observation_datetime],
    )


def insert_visit_observation_types() -> None:
    vot_names = ("HEIGHT", "WEIGHT/SCALE", "R GLASGOW COMA SCALE SCORE")
    for name, vot_id in zip(
        vot_names, (height_vot_id, weight_vot_id, gcs_vot_id), strict=True
    ):
        insert_row_into_emap_star_schema(
            "visit_observation_type",
            ["visit_observation_type_id", "name"],
            [vot_id, name],
        )


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
    insert_visit_observation_types()
    insert_visit_observation(type_id=height_vot_id, value=height)
    insert_visit_observation(type_id=weight_vot_id, value=weight)
    insert_visit_observation(type_id=gcs_vot_id, value=float(gcs))

    insert_row_into_emap_star_schema(
        "lab_sample",
        ["lab_sample_id", "external_lab_number", "mrn_id"],
        [ls_id, accession_number, mrn_id],
    )
    insert_row_into_emap_star_schema(
        "lab_order", ["lab_order_id", "lab_sample_id"], [lo_id, ls_id]
    )
    insert_row_into_emap_star_schema(
        "lab_test_definition",
        ["lab_test_definition_id", "test_lab_code"],
        [ltd_id, "NARRATIVE"],
    )
    insert_row_into_emap_star_schema(
        "lab_result",
        ["lab_result_id", "lab_order_id", "lab_test_definition_id", "value_as_text"],
        [lr_id, lo_id, ltd_id, report_text],
    )


@pytest.mark.processing()
@pytest.mark.asyncio()
async def test_message_processing() -> None:
    insert_data_into_emap_star_schema()
    await process_message(message_body)

    pixl_db = QueryablePIXLDB()
    row = pixl_db.execute_query_string(
        "select * from emap_data.ehr_raw where mrn = %s", [mrn]
    )

    expected_row = [
        mrn,
        accession_number,
        "any",
        sex,
        ethnicity,
        height,
        weight,
        gcs,
        report_text,
    ]

    for value, expected_value in zip(row, expected_row, strict=True):
        if expected_value == "any":
            continue  # Skip the age, because that depends on the current date...

        assert value == expected_value

    anon_row = pixl_db.execute_query_string(
        "select * from emap_data.ehr_anon where gcs = %s", [gcs]
    )
    anon_mrn, anon_accession_number = anon_row[:2]
    assert anon_mrn != mrn
    assert anon_accession_number != accession_number
    assert name_of_doctor not in anon_row[-1]
