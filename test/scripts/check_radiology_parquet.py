#!/usr/bin/env python
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
from pathlib import Path

import pandas as pd
import sys

expected_parquet_file = sys.argv[1]
exported_data = pd.read_parquet(expected_parquet_file)

print(exported_data.head())

parquet_header_names = ["image_identifier", "procedure_occurrence_id", "image_report"]

# the fake DEID service adds this string to the end to confirm it has been through it
DE_ID_SUFFIX = '**DE-IDENTIFIED**'

expected_rows = 2
assert exported_data.shape[0] == expected_rows

assert exported_data.loc[0].procedure_occurrence_id == 4
assert exported_data.loc[0].image_report == 'this is a radiology report 1' + DE_ID_SUFFIX

# assert exported_data.loc[0].image_identifier == 'a971b114b9133c81c03fb88c6a958f7d95eb1387f04c17'

assert exported_data.loc[1].procedure_occurrence_id == 5
assert exported_data.loc[1].image_report == 'this is a radiology report 2' + DE_ID_SUFFIX

# Files must not be owned by root - they'll be hard to delete and we shouldn't be running our
# containers as root anyway.
file_stats = Path(expected_parquet_file).stat()
assert file_stats.st_uid != 0
assert file_stats.st_gid != 0

# assert exported_data.loc[1].image_identifier == 'f71b228fa97d6c87db751e0bb35605fd9d4c1274834be4'
