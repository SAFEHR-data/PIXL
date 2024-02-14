#!/bin/bash
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

set -euxo pipefail

# Create the EHR schema and associated tables
columns_and_types="mrn text, accession_number text, image_identifier text, procedure_occurrence_id integer, age integer, sex text, ethnicity text, height real, weight real, gcs integer, xray_report text, project_name text, extract_datetime timestamp"
ehr_create_command="CREATE SCHEMA emap_data AUTHORIZATION ${POSTGRES_USER}
    CREATE TABLE ehr_raw ($columns_and_types)
    CREATE TABLE ehr_anon ($columns_and_types)
"
psql -U "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" -c "$ehr_create_command"

source /pixl/venv/bin/activate