"""
Add fake DICOM data to an Orthanc instance
"""
import os
import numpy as np
import pydicom

from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid
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

    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 216
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.MediaStorageSOPClassUID = generate_uid()
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = generate_uid()

    # Main data elements
    ds = Dataset()
    ds.ImageType = ['ORIGINAL', 'SECONDARY']
    ds.AcquisitionDateTime = datetime

    ds.AccessionNumber = accession_id
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyInstanceUID = generate_uid()
    ds.FrameOfReferenceUID = generate_uid()

    ds.PatientID = str(mrn_id)
    ds.SOPInstanceUID = generate_uid()

    # Source Image Sequence
    source_image_sequence = Sequence()
    ds.SourceImageSequence = source_image_sequence

    # Source Image Sequence: Source Image 1
    source_image1 = Dataset()
    source_image_sequence.append(source_image1)

    random_pixel_array = np.random.randint(
       low=0,
       high=65534,  # 1 minus the upper bound for uint16
       size=(256, 256),
       dtype=np.uint16
    )
    ds.Rows = random_pixel_array.shape[0]
    ds.Columns = random_pixel_array.shape[1]
    ds.InstanceNumber = 1
    ds.PixelData = random_pixel_array

    ds.file_meta = file_meta
    ds.is_implicit_VR = True
    ds.is_little_endian = True

    pydicom.dataset.validate_file_meta(ds.file_meta, enforce_standard=True)

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
