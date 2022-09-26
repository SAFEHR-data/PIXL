"""
Given an MRN and accession number, defining the patient and associated
x-ray study obtain electronic health record (EHR) data
along with the corresponding report.
"""
import argparse
import pandas as pd

from pathlib import Path
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass
from pyorthanc import find
from core import _env_var, QueryableDatabase, SQLQuery


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


class Step(ABC):

    @abstractmethod
    def update(self, data: PatientEHRData) -> None:
        """Update the data on a patient for this step"""


class AcquisitionTimes(list):
    """
    List of times, which can be appended to with raw strings in the
    form:
        "20220501000000.000000"

    and an average taken.
    """

    def average(self) -> datetime:
        """Compute the average (mean) of all the times in this series"""

        pd_series = pd.Series(data=self)
        pd_avg_time = pd.to_datetime(pd_series, format='%Y%m%d%H%M%S.%f').mean()
        return pd_avg_time.to_pydatetime()


class SetAcquisitionTime(Step):
    _orthanc_url = f"http://{_env_var('ORTHANC_URL')}:{_env_var('ORTHANC_RAW_WEB_PORT')}"
    _orthanc_auth = (_env_var("ORTHANC_USERNAME"), _env_var("ORTHANC_PASSWORD"))

    def update(self, data: PatientEHRData) -> None:
        """Update the data with an acquisition time"""

        def mrn_matches(patient: "pyorthanc.patient.Patient") -> bool:
            return patient.patient_id == str(data.mrn)

        def accession_number_matches(study: "pyorthanc.study.Study") -> bool:
            _tags = study.get_main_information()['MainDicomTags']
            return _tags['AccessionNumber'] == str(data.accession_number)

        patients = find(
            orthanc_url=self._orthanc_url,
            auth=self._orthanc_auth,
            patient_filter=mrn_matches,
            study_filter=accession_number_matches

        )

        try:
            assert len(patients) == 1
            assert len(patients[0].studies) == 1
        except AssertionError:
            print("ERROR: Failed to find a unique study")  # TODO: convert to nice logging

        study = patients[0].studies[0]
        times = AcquisitionTimes()
        for series in study.series:
            for instance in series.instances:
                try:
                    times.append(
                        instance.simplified_tags['AcquisitionDateTime']
                    )
                except KeyError:
                    print("WARNING: DICOM instance did not have an "
                          "AcquisitionDateTime tag set")

        if len(times) > 0:
            data.acquisition_datetime = times.average()
        else:
            print("WARNING: Found no times in DICOM study")

        return None


class EMAPStep(Step, ABC):

    def __init__(self, db: QueryableDatabase):
        self.db = db


class SetAgeSexEthnicity(EMAPStep):

    def update(self, data: PatientEHRData) -> None:
        """Update the data with age, sex and ethnicity"""

        query = SQLQuery(
            filepath=Path('../sql/mrn_to_DOB_sex_ethnicity.sql'),
            context={"schema_name": _env_var("EMAP_UDS_SCHEMA_NAME"),
                     "mrn": data.mrn
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

    def __init__(self, db: QueryableDatabase, time_cutoff_n_days: int):
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
            filepath=Path('../sql/mrn_timewindow_to_observationtype.sql'),
            context={"schema_name": _env_var("EMAP_UDS_SCHEMA_NAME"),
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
        return "WEIGHT"


class SetGCS(SetVOT):

    @property
    def name(self) -> str:
        return "glasgow_coma_scale"

    @property
    def emap_name(self) -> str:
        return "R GLASGOW COMA SCALE SCORE"


class Pipeline:

    def __init__(self, *steps: Step):
        self.steps = steps

    def run(self, data: PatientEHRData) -> None:

        for step in self.steps:

            try:
                step.update(data)
            except Exception as e:  # blanket except..
                print(f"ERROR: {e}")

        return None


def parse_args() -> argparse.Namespace:
    """Parse command line arguments and return a namespace"""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-m',
        '--mrn',
        type=str,
        required=True,
        help="Patient identifier. aka. MRN, PatientID"
    )
    parser.add_argument(
        '-a',
        '--accession_number',
        type=str,
        required=True,
        help="Xray report identifier. aka AccessionNumber "
    )
    parser.add_argument(
        '-w',
        '--weight_time_cutoff',
        required=True,
        help="Time cutoff in *days* for a weight observation on a patient. "
             "i.e. a weight known 2 days before or after the xray acquisition "
             "will be discarded"
    )
    parser.add_argument(
        '-t',
        '--height_time_cutoff',
        required=True,
        help="Time cutoff in *days* for a height observation on a patient"
    )
    parser.add_argument(
        '-g',
        '--gcs_time_cutoff',
        required=True,
        help="Time cutoff in *days* for a Glasgow coma scale observation "
             "on a patient"
    )

    return parser.parse_args()


def main():

    args = parse_args()

    data = PatientEHRData(
        mrn=args.mrn,
        accession_number=args.accession_number
    )
    db = QueryableDatabase()

    pipeline = Pipeline(
        SetAcquisitionTime(),
        SetAgeSexEthnicity(db),
        SetHeight(db, time_cutoff_n_days=args.height_time_cutoff),
        SetWeight(db, time_cutoff_n_days=args.weight_time_cutoff),
        SetGCS(db, time_cutoff_n_days=args.gcs_time_cutoff),
    )
    pipeline.run(data)

    print(vars(data))

    return None


if __name__ == '__main__':
    main()
