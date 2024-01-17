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
import pandas as pd
import sys

expected_parquet_file = sys.argv[1]
exported_data = pd.read_parquet(expected_parquet_file)

print(exported_data.head())

parquet_header_names = ["image_identifier", "procedure_occurrence_id", "image_report"]

expected_rows = 2
assert exported_data.shape[0] == expected_rows

assert exported_data.loc[0].procedure_occurrence_id == 4
assert exported_data.loc[0].image_report == 'this is a radiology report 1'

assert exported_data.loc[0].image_identifier == ''

assert exported_data.loc[1].procedure_occurrence_id == 5
assert exported_data.loc[1].image_report == 'this is a radiology report 2'

assert exported_data.loc[1].image_identifier == ''
