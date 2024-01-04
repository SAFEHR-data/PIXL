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
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import requests

if TYPE_CHECKING:
    from core.patient_queue.message import Message
from core.omop import ParquetExport
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
    logger.info("Processing: %s", message)

    raw_data = PatientEHRData.from_message(message)
    pixl_db = PIXLDatabase()

    if pixl_db.contains(raw_data):
        logger.info("Message has already been processed")
        return

    emap_star_db = EMAPStar()

    pipeline = ProcessingPipeline(
        SetAgeSexEthnicity(emap_star_db),
        SetHeight(emap_star_db, time_cutoff_n_days=1),
        SetWeight(emap_star_db, time_cutoff_n_days=1),
        SetGCS(emap_star_db, time_cutoff_n_days=1),
        SetReport(emap_star_db),
    )
    raw_data.update_using(pipeline)

    raw_data.persist(pixl_db, schema_name="emap_data", table_name="ehr_raw")
    anon_data = raw_data.anonymise()
    anon_data.persist(pixl_db, schema_name="emap_data", table_name="ehr_anon")


def export_radiology_reports(anon_data: Iterable[tuple]) -> None:
    # might need to generate the study ID slug here?
    pe = ParquetExport(project_name, extract_datetime)
    pe.export_radiology(anon_data)


@dataclass
class PatientEHRData:
    """Dataclass for EHR unique to a patient and xray study"""

    mrn: str
    accession_number: str
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
            except Exception as e:  # noqa: BLE001
                logger.warning(e)

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
            "age",
            "sex",
            "ethnicity",
            "height",
            "weight",
            "gcs",
            "xray_report",
        ]

        cols = ",".join(col_names)
        vals = ",".join("%s" for _ in range(len(col_names)))

        database.persist(
            f"INSERT INTO {schema_name}.{table_name} ({cols}) VALUES ({vals})",
            [
                self.mrn,
                self.accession_number,
                self.age,
                self.sex,
                self.ethnicity,
                self.height,
                self.weight,
                self.glasgow_coma_scale,
                self.report_text,
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


class SetAgeSexEthnicity(EMAPStep):
    def update(self, data: PatientEHRData) -> None:
        """Update the data with age, sex and ethnicity"""
        query = SQLQuery(
            filepath=Path(_this_dir, "sql/mrn_to_DOB_sex_ethnicity.sql"),
            context={
                "schema_name": config("EMAP_UDS_SCHEMA_NAME"),
                "mrn": data.mrn,
                "window_midpoint": data.acquisition_datetime,
            },
        )
        result = self.db.execute_or_raise(query, "No demographic data")
        date_of_birth, data.sex, data.ethnicity = result

        if data.acquisition_datetime is None:
            logger.warning("WARNING: Cannot set the age without an acquisition time")
            return

        acquisition_date = data.acquisition_datetime.date()
        data.age = (
            acquisition_date - date_of_birth
        ).days / 365.2425  # Average days per year. Accurate enough


class SetVOT(EMAPStep, ABC):
    def __init__(self, db: EMAPStar, time_cutoff_n_days: int) -> None:
        super().__init__(db=db)

        self.time_cutoff_n_days = int(time_cutoff_n_days)

    def time_window_start(self, from_time: datetime) -> datetime:
        return from_time - timedelta(self.time_cutoff_n_days)

    def time_window_end(self, from_time: datetime) -> datetime:
        return from_time + timedelta(self.time_cutoff_n_days)

    @property
    @abstractmethod
    def name(self) -> str:
        """Common name of the observation type e.g. height"""

    @property
    @abstractmethod
    def emap_name(self) -> str:
        """Name of this observation type in an EMAP star schema, e.g. HEIGHT"""

    def update(self, data: PatientEHRData) -> None:
        if data.acquisition_datetime is None:
            msg = "Cannot update a height without an acquisition"
            raise RuntimeError(msg)

        query = SQLQuery(
            filepath=Path(_this_dir, "sql/mrn_timewindow_to_observationtype.sql"),
            context={
                "schema_name": config("EMAP_UDS_SCHEMA_NAME"),
                "mrn": data.mrn,
                "observation_type": self.emap_name,
                "window_start": self.time_window_start(from_time=data.acquisition_datetime),
                "window_end": self.time_window_end(from_time=data.acquisition_datetime),
                "window_midpoint": data.acquisition_datetime,
            },
        )
        result = self.db.execute_or_raise(query, f"No {self.name}")
        setattr(data, self.name, result[0])  # e.g. data.height = result[0]


class SetHeight(SetVOT):
    @property
    def name(self) -> str:
        return "height"

    @property
    def emap_name(self) -> str:
        return "HEIGHT"


class SetWeight(SetVOT):
    @property
    def name(self) -> str:
        return "weight"

    @property
    def emap_name(self) -> str:
        return "WEIGHT/SCALE"


class SetGCS(SetVOT):
    @property
    def name(self) -> str:
        return "glasgow_coma_scale"

    @property
    def emap_name(self) -> str:
        return "R GLASGOW COMA SCALE SCORE"


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
