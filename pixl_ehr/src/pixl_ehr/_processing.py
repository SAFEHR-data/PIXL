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
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import requests

if TYPE_CHECKING:
    from datetime import datetime

    from core.patient_queue.message import Message
from decouple import config

from pixl_ehr._databases import EMAPStar, PIXLDatabase
from pixl_ehr._queries import SQLQuery

from .report_deid import deidentify_text

if TYPE_CHECKING:
    from core.patient_queue.message import Message

logger = logging.getLogger("uvicorn")
logger.setLevel(os.environ.get("LOG_LEVEL", "WARNING"))

_this_dir = Path(Path(__file__).parent)


async def process_message(message: Message) -> None:
    logger.debug("Processing: %s", message)

    raw_data = PatientEHRData.from_message(message)
    pixl_db = PIXLDatabase()

    if pixl_db.contains(raw_data):
        logger.debug("Message has already been processed")
        return

    emap_star_db = EMAPStar()

    pipeline = ProcessingPipeline(
        SetReport(emap_star_db),
    )
    raw_data.update_using(pipeline)

    raw_data.persist(pixl_db, schema_name="emap_data", table_name="ehr_raw")
    anon_data = raw_data.anonymise()
    anon_data.persist(pixl_db, schema_name="emap_data", table_name="ehr_anon")


@dataclass
class PatientEHRData:
    """Dataclass for EHR unique to a patient and xray study"""

    mrn: str
    accession_number: str
    image_identifier: str
    procedure_occurrence_id: int
    project_name: str
    extract_datetime: datetime
    acquisition_datetime: Optional[datetime]

    age: Optional[int] = None
    sex: Optional[str] = None
    ethnicity: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    glasgow_coma_scale: Optional[int] = None

    report_text: Optional[str] = None

    @classmethod
    def from_message(cls, message: Message) -> PatientEHRData:
        """
        Create a minimal set of patient EHR data required to start queries from a
        queue message
        """
        self = PatientEHRData(
            mrn=message.mrn,
            accession_number=message.accession_number,
            image_identifier=message.mrn + message.accession_number,
            procedure_occurrence_id=message.procedure_occurrence_id,
            project_name=message.project_name,
            extract_datetime=message.omop_es_timestamp,
            acquisition_datetime=message.study_date,
        )

        logger.debug("Created %s from message data", self)
        return self

    def update_using(self, pipeline: ProcessingPipeline) -> None:
        """Update these data using a processing pipeline"""
        for i, step in enumerate(pipeline.steps):
            logger.debug("Step %s", [i / len(pipeline.steps) - 1])

            try:
                step.update(self)
            except Exception:
                logger.exception("pipeline step failed")

    def persist(self, database: PIXLDatabase, schema_name: str, table_name: str) -> None:
        """Persist a.k.a. save some data in a database"""
        logger.debug(
            "Persisting EHR and report data into %s.%s.%s",
            database,
            schema_name,
            table_name,
        )

        col_names = [
            "mrn",
            "accession_number",
            "image_identifier",
            "procedure_occurrence_id",
            "age",
            "sex",
            "ethnicity",
            "height",
            "weight",
            "gcs",
            "xray_report",
            "project_name",
            "extract_datetime",
        ]

        cols = ",".join(col_names)
        vals = ",".join("%s" for _ in range(len(col_names)))

        database.persist(
            f"INSERT INTO {schema_name}.{table_name} ({cols}) VALUES ({vals})",
            [
                self.mrn,
                self.accession_number,
                self.image_identifier,
                self.procedure_occurrence_id,
                self.age,
                self.sex,
                self.ethnicity,
                self.height,
                self.weight,
                self.glasgow_coma_scale,
                self.report_text,
                self.project_name,
                self.extract_datetime,
            ],
        )
        logger.debug("Persist successful!")

    def anonymise(self) -> PatientEHRData:
        """Anonymise these patient data by processing text and hashing identifiers"""
        if self.report_text is not None:
            self.report_text = deidentify_text(self.report_text)

        self.mrn = pixl_hash(self.mrn, endpoint_path="hash-mrn")
        self.accession_number = pixl_hash(
            self.accession_number, endpoint_path="hash-accession-number"
        )
        self.image_identifier = pixl_hash(self.image_identifier, endpoint_path="hash")
        self.acquisition_datetime = None

        return self

    def copy(self) -> PatientEHRData:
        return deepcopy(self)


class Step(ABC):
    @abstractmethod
    def update(self, data: PatientEHRData) -> None:
        """Update the data on a patient for this step"""


class EMAPStep(Step, ABC):
    def __init__(self, db: EMAPStar) -> None:
        self.db = db


class SetReport(EMAPStep):
    def update(self, data: PatientEHRData) -> None:
        """Update the data with age, sex and ethnicity"""
        query = SQLQuery(
            filepath=Path(_this_dir, "sql/mrn_accession_to_report.sql"),
            context={
                "schema_name": config("EMAP_UDS_SCHEMA_NAME"),
                "mrn": data.mrn,
                "accession_number": data.accession_number,
            },
        )
        data.report_text = self.db.execute_or_raise(query, "No report text found")[0]


class ProcessingPipeline:
    def __init__(self, *steps: Step) -> None:
        self.steps = steps


def pixl_hash(string: str, endpoint_path: str) -> str:
    """Use the PIXL hashing API to hash a string"""
    response = requests.get(
        f"http://hasher-api:8000/{endpoint_path.lstrip('/')}",
        params={"message": string},
        timeout=10,
    )
    success_code = 200
    if response.status_code == success_code:
        logger.debug("Hashed to %s", response.text)
        return response.text

    msg = f"Failed to hash {string}"
    raise RuntimeError(msg)
