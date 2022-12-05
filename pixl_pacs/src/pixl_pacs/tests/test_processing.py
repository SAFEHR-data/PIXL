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
import os

from pixl_pacs._orthanc import Orthanc
from pixl_pacs.utils import env_var
from pydicom import dcmread
from pydicom.data import get_testdata_file
from requests import post


class WritableOrthanc(Orthanc):
    def upload(self, filename: str) -> None:
        os.system(
            f"curl -u {self._username}:{self._password} "
            f"-X POST {self._url}/instances --data-binary @{filename}"
        )


def add_image_to_vna(image_filename: str = "test.dcm") -> None:
    path = get_testdata_file("CT_small.dcm")
    ds = dcmread(path)  # type: ignore
    ds.save_as(image_filename)

    vna = WritableOrthanc(
        url=f"http://vna-qr:8042",
        username=env_var("ORTHANC_VNA_USERNAME"),
        password=env_var("ORTHANC_VNA_PASSWORD"),
    )
    vna.upload(image_filename)


def test_image_processing() -> None:

    add_image_to_vna()
