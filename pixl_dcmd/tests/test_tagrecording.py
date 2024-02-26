#  Copyright (c) 2024 University College London Hospitals NHS Foundation Trust
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

import csv
import os

from pytest_pixl.dicom import generate_dicom_dataset
from pixl_dcmd.main import write_dataset_to_bytes
from pixl_dcmd.tagrecording import record_dicom_headers


def test_record_dicom_headers(mock_header_record_path):
    ds = generate_dicom_dataset()
    ds_bytes = write_dataset_to_bytes(ds)
    record_dicom_headers(ds_bytes)
    with open(os.environ.get("ORTHANC_RAW_HEADER_LOG_PATH", "/tmp"), "r") as f:
        reader = csv.reader(f)
        row = next(reader)
        assert row == ["Company", "NA", "NA", "NA", "mri_sequence", "NA"]
