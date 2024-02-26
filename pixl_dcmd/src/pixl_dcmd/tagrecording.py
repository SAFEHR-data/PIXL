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
"""Functions to record DICOM headers to a file."""

import importlib.resources
from io import BytesIO
from pathlib import Path
import os

from pydicom import dcmread

import yaml


def record_dicom_headers(receivedDicom: bytes) -> None:
    with importlib.resources.files("pixl_dcmd").joinpath(
        "resources/recorded-headers.yml"
    ).open() as f:
        recording_config = yaml.safe_load(f)
    dataset = dcmread(BytesIO(receivedDicom), force=True)
    with _header_log_path().open("a") as f:
        values = [str(dataset.get(tag, "NA")) for tag in recording_config["tags"]]
        f.write(",".join(values) + "\n")


def _header_log_path() -> Path:
    return Path(os.environ.get("ORTHANC_RAW_HEADER_LOG_PATH", "/dev/null"))
