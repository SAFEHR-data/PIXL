"""
Add fake DICOM data to an Orthanc instance
"""
import os
import numpy as np
import pydicom

from pydicom import dcmread
from pydicom.data import get_testdata_file
from pyorthanc import Orthanc
from pathlib import Path
from core import _env_var
from test_data import ACCESSION_NUMBERS, MRNs


data = {
   "accession_number": ACCESSION_NUMBERS,
   "mrn": MRNs,
   "datetime": ['20220501000000.000000', '20220601000000.000000', '20220701000000.000000']
}


def save_random_dicom_file(filepath: Path,
                           accession_id: str,
                           mrn_id: int,
                           datetime: str
                           ) -> None:
    """Given a filepath generate a random DICOM instance"""

    path = get_testdata_file("CT_small.dcm")
    ds = dcmread(path)

    ds.AcquisitionDateTime = datetime
    ds.AccessionNumber = accession_id
    ds.PatientID = str(mrn_id)

    ds.save_as(str(filepath), write_like_original=False)
    return None


def main():
    orthanc = Orthanc(
        url=f"http://{_env_var('ORTHANC_URL')}:{_env_var('ORTHANC_RAW_WEB_PORT')}",
        username=_env_var("ORTHANC_USERNAME"),
        password=_env_var("ORTHANC_PASSWORD")
    )

    for i in range(len(ACCESSION_NUMBERS)):

        path = Path("tmp.cdm")
        save_random_dicom_file(
            filepath=path,
            mrn_id=data["mrn"][i],
            accession_id=data["accession_number"][i],
            datetime=data["datetime"][i]
        )

        with open(path, 'rb') as file:
            print(f"Posting instance {i} to {orthanc.url}")
            orthanc.post_instances(file.read())

        os.remove(path)

    print("Successfully added the fake DICOM")
    return None


if __name__ == '__main__':
    main()
