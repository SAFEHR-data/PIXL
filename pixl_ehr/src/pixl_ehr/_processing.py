import os
import logging

from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional
from pixl_ehr._databases import EMAPStar
from pixl_ehr._queries import SQLQuery
from pixl_ehr.utils import env_var

logger = logging.getLogger("uvicorn")
logger.setLevel(os.environ.get("LOG_LEVEL", "WARNING"))

_this_dir = Path(os.path.dirname(__file__))


# TODO: move to patient queue package
def deserialise(message_body: bytes):
    logger.debug(f"De-serialising: {message_body}")

    parts = message_body.decode().split(",")
    return {
        "mrn": parts[0],
        "accession_number": parts[1],
        "study_datetime": datetime.strptime(parts[2], '%d/%m/%Y %H:%M:%S')
    }


def process_message(message_body: bytes) -> None:
    logger.info(f"Processing: {message_body}")

    data = PatientEHRData.from_message(message_body)
    db = EMAPStar()

    pipeline = ProcessingPipeline(
        SetAgeSexEthnicity(db),
        SetHeight(db, time_cutoff_n_days=1),
        SetWeight(db, time_cutoff_n_days=1),
        SetGCS(db, time_cutoff_n_days=1),
        SetReport(db)
    )
    pipeline.run(data)

    print(vars(data))

    return None


@dataclass
class PatientEHRData:
    """Dataclass for EHR unique to a patient and xray study"""

    mrn: str                # | Required identifiers
    accession_number: str   # |
    acquisition_datetime: Optional[datetime] = None

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
            acquisition_datetime=message_data["study_datetime"]
        )

        logger.debug(f"Created {self} from message data")
        return self


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
            filepath=Path(_this_dir, 'sql/mrn_to_DOB_sex_ethnicity.sql'),
            context={"schema_name": env_var("EMAP_UDS_SCHEMA_NAME"),
                     "mrn": data.mrn,
                     "window_midpoint": data.acquisition_datetime
                     }
        )
        result = self.db.execute_or_raise(query, "No demographic data")
        date_of_birth, data.sex, data.ethnicity = result

        if data.acquisition_datetime is None:
            print("WARNING: Cannot set the age without an acquisition time")
            return

        acquisition_date = data.acquisition_datetime.date()
        data.age = ((acquisition_date - date_of_birth).days
                    / 365.2425)  # Average days per year. Accurate enough

        return None


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
            filepath=Path(_this_dir, 'sql/mrn_timewindow_to_observationtype.sql'),
            context={"schema_name": env_var("EMAP_UDS_SCHEMA_NAME"),
                     "mrn": data.mrn,
                     "observation_type": self.emap_name,
                     "window_start": self.time_window_start(from_time=data.acquisition_datetime),
                     "window_end": self.time_window_end(from_time=data.acquisition_datetime),
                     "window_midpoint": data.acquisition_datetime
                     }
        )
        result = self.db.execute_or_raise(query, f"No {self.name}")
        setattr(data, self.name, result[0])  # e.g. data.height = result[0]
        return None


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
            filepath=Path(_this_dir, 'sql/mrn_accession_to_report.sql'),
            context={"schema_name": env_var("EMAP_UDS_SCHEMA_NAME"),
                     "mrn": data.mrn,
                     "accession_number": data.accession_number
                     }
        )
        data.report_text = self.db.execute_or_raise(query, "No report text found")
        return None


class ProcessingPipeline:

    def __init__(self, *steps: Step):
        self.steps = steps

    def run(self, data: PatientEHRData) -> None:

        for step in self.steps:

            try:
                step.update(data)
            except Exception as e:  # blanket except..
                print(f"ERROR: {e}")

        return None
