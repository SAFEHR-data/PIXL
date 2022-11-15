"""
These tests require executing from within the EHR API container with the dependent
services being up
    - pixl postgres db
    - emap star
"""
from datetime import datetime
from typing import List

from pixl_ehr._databases import PIXLDatabase, WriteableDatabase
from pixl_ehr._processing import process_message
from pixl_ehr.utils import env_var
from psycopg2.errors import UniqueViolation

mrn = "testmrn"
accession_number = "testaccessionnumber"
study_datetime = "01/01/1234 01:23:45"
observation_datetime = datetime.fromisoformat(
    "1234-01-01"
)  # within hours of imaging study
date_of_birth = "09/08/0007"
sex = "testsexvalue"
ethnicity = "testethnicity"
height = 123.0
weight = 45.0
gcs = 6
report_text = "test\nxray report\nsigned by John Smith"

# Primary/foreign keys used to insert linked mrns, hospital visits, labs
# visit observation types
mrn_id = 9999999
hv_id = 1111111
weight_vot_id, height_vot_id, gcs_vot_id = 2222222, 3333333, 4444444
ls_id, lo_id, lr_id, ltd_id = 5555555, 6666666, 7777777, 8888888

# TODO: replace with serialisation function
message_body = f"{mrn},{accession_number},{study_datetime}".encode("utf-8")


class WritableEMAPStar(WriteableDatabase):
    def __init__(self) -> None:
        super().__init__(
            db_name=env_var("EMAP_UDS_NAME"),
            username=env_var("EMAP_UDS_USER"),
            password=env_var("EMAP_UDS_PASSWORD"),
            host=env_var("EMAP_UDS_HOST"),
        )

        if env_var("EMAP_UDS_HOST") != "star":
            raise RuntimeError(
                "It looks like the host was not a docker-compose "
                "created service. Cannot create a writable EMAPStar"
            )


class QueryablePIXLDB(PIXLDatabase):
    def execute(self, query: str, values: list) -> tuple:
        self._cursor.execute(query=query, vars=values)
        row = self._cursor.fetchone()
        return tuple(row)


def insert_row_into_emap_star_schema(
    table_name: str, col_names: List[str], values: List
) -> None:

    db = WritableEMAPStar()
    cols = ",".join(col_names)
    vals = ",".join("%s" for _ in range(len(col_names)))

    try:
        db.persist(
            f"INSERT INTO star.{table_name} ({cols}) VALUES ({vals})",
            values,
        )
    except UniqueViolation:
        pass  # If it's already there then all is okay, hopefully


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
    for name, vot_id in zip(vot_names, (height_vot_id, weight_vot_id, gcs_vot_id)):
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
        "lab_order", ["lab_order_id", "lab_sample_id"], [lo_id, ls_id]
    )
    insert_row_into_emap_star_schema(
        "lab_result",
        ["lab_result_id", "lab_order_id", "lab_test_definition_id", "value_as_text"],
        [lr_id, lo_id, ltd_id, report_text],
    )
    insert_row_into_emap_star_schema(
        "lab_test_definition",
        ["lab_test_definition_id", "test_lab_code"],
        [ltd_id, "TEXT"],
    )
    insert_row_into_emap_star_schema(
        "lab_sample",
        ["lab_sample_id", "external_lab_number", "mrn_id"],
        [ls_id, accession_number, mrn_id],
    )


def test_message_processing() -> None:

    insert_data_into_emap_star_schema()
    process_message(message_body)

    pixl_db = QueryablePIXLDB()
    row = pixl_db.execute("select * from emap_data.ehr_raw where mrn = %s", [mrn])

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

    for value, expected_value in zip(row, expected_row):
        if expected_value == "any":
            continue  # Skip the age, because that depends on the current date...

        assert value == expected_value
