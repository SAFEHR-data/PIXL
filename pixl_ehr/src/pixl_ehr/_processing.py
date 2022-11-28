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
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
from typing import Optional

from pixl_ehr._databases import EMAPStar, PIXLDatabase
from pixl_ehr._queries import SQLQuery
from pixl_ehr.utils import env_var
import requests

from pixl_rd import deidentify_text

logger = logging.getLogger("uvicorn")
logger.setLevel(os.environ.get("LOG_LEVEL", "WARNING"))

_this_dir = Path(os.path.dirname(__file__))


def process_message(message_body: bytes) -> None:
    logger.info(f"Processing: {message_body.decode()}")

    raw_data = PatientEHRData.from_message(message_body)
    emap_star_db = EMAPStar()

    pipeline = ProcessingPipeline(
        SetAgeSexEthnicity(emap_star_db),
        SetHeight(emap_star_db, time_cutoff_n_days=1),
        SetWeight(emap_star_db, time_cutoff_n_days=1),
        SetGCS(emap_star_db, time_cutoff_n_days=1),
        SetReport(emap_star_db),
    )
    raw_data.update_using(pipeline)

    pixl_db = PIXLDatabase()

    raw_data.persist(pixl_db, schema_name="emap_data", table_name="ehr_raw")
    anon_data = raw_data.anonymise()
    anon_data.persist(pixl_db, schema_name="emap_data", table_name="ehr_anon")


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
    def from_message(cls, message_body: bytes) -> "PatientEHRData":
        """
        Create a minimal set of patient EHR data required to start queries from a
        queue message
        """

        message_data = deserialise(message_body)
        self = PatientEHRData(
            mrn=message_data["mrn"],
            accession_number=message_data["accession_number"],
            acquisition_datetime=message_data["study_datetime"],
        )

        logger.debug(f"Created {self} from message data")
        return self

    def update_using(self, pipeline: "ProcessingPipeline") -> None:
        """Update these data using a processing pipeline"""

        for i, step in enumerate(pipeline.steps):
            logger.debug(f"Step [{i}/{len(pipeline.steps) - 1}]")

            try:
                step.update(self)
            except Exception as e:  # no-qa
                logger.warning(e)

    def persist(
        self, database: PIXLDatabase, schema_name: str, table_name: str
    ) -> None:
        """Persist a.k.a. save some data in a database"""
        logger.debug(
            f"Persisting EHR and report data into "
            f"{database}.{schema_name}.{table_name}"
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

    def anonymise(self) -> "PatientEHRData":
        """Anonymise these patient data by processing text and hashing identifiers"""

        if self.report_text is not None:
            self.report_text = deidentify_text(self.report_text)

        self.mrn = pixl_hash(self.mrn)
        self.accession_number = pixl_hash(self.accession_number)
        self.acquisition_datetime = None

        return self

    def copy(self) -> "PatientEHRData":
        return deepcopy(self)


class Step(ABC):
    @abstractmethod
    def update(self, data: PatientEHRData) -> None:
        """Update the data on a patient for this step"""


class EMAPStep(Step, ABC):
    def __init__(self, db: EMAPStar):
        self.db = db


class SetAgeSexEthnicity(EMAPStep):
    def update(self, data: PatientEHRData) -> None:
        """Update the data with age, sex and ethnicity"""

        query = SQLQuery(
            filepath=Path(_this_dir, "sql/mrn_to_DOB_sex_ethnicity.sql"),
            context={
                "schema_name": env_var("EMAP_UDS_SCHEMA_NAME"),
                "mrn": data.mrn,
                "window_midpoint": data.acquisition_datetime,
            },
        )
        result = self.db.execute_or_raise(query, "No demographic data")
        date_of_birth, data.sex, data.ethnicity = result

        if data.acquisition_datetime is None:
            print("WARNING: Cannot set the age without an acquisition time")
            return

        acquisition_date = data.acquisition_datetime.date()
        data.age = (
            acquisition_date - date_of_birth
        ).days / 365.2425  # Average days per year. Accurate enough


class SetVOT(EMAPStep, ABC):
    def __init__(self, db: EMAPStar, time_cutoff_n_days: int):
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
            raise RuntimeError("Cannot update a height without an acquisition")

        query = SQLQuery(
            filepath=Path(_this_dir, "sql/mrn_timewindow_to_observationtype.sql"),
            context={
                "schema_name": env_var("EMAP_UDS_SCHEMA_NAME"),
                "mrn": data.mrn,
                "observation_type": self.emap_name,
                "window_start": self.time_window_start(
                    from_time=data.acquisition_datetime
                ),
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
                "schema_name": env_var("EMAP_UDS_SCHEMA_NAME"),
                "mrn": data.mrn,
                "accession_number": data.accession_number,
            },
        )
        data.report_text = self.db.execute_or_raise(query, "No report text found")[0]


class ProcessingPipeline:
    def __init__(self, *steps: Step):
        self.steps = steps


# TODO: move to patient queue package
def deserialise(message_body: bytes) -> dict:
    logger.debug(f"De-serialising: {message_body.decode()}")

    parts = message_body.decode().split(",")
    return {
        "mrn": parts[0],
        "accession_number": parts[1],
        "study_datetime": datetime.strptime(parts[2], "%d/%m/%Y %H:%M:%S"),
    }


def pixl_hash(string: str) -> str:
    """Use the PIXL hashing API to hash a string"""

    response = requests.get("http://hasher-api:8000/hash", params={"message": string})

    if response.status_code == 200:
        logger.debug(f"Hashed to {response.text}")
        return response.text

    raise RuntimeError(f"Failed to hash {string}")
