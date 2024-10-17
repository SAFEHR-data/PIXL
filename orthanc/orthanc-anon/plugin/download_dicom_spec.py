#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
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
"""Download the DICOM spec with dicom-validator."""

from pathlib import Path

from dicom_validator.spec_reader.edition_reader import EditionReader

edition = "current"
download_path = str(Path.home() / "dicom-validator")
edition_reader = EditionReader(download_path)
destination = edition_reader.get_revision(edition, recreate_json=False)
json_path = Path(destination, "json")
EditionReader.load_dicom_info(json_path)
