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

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

_sql_command="
insert into star.mrn(mrn_id, mrn, research_opt_out) values (1234, 'patient_identifier', false);
insert into star.core_demographic(mrn_id, sex) values (1234, 'F');
"
docker exec -it test-fake-star-db /bin/bash -c "psql -U postgres -d emap -c \"$_sql_command\"" || true

# Uses an accession number of "123456789"
curl -X POST -u orthanc:orthanc http://localhost:8043/instances \
  --data-binary @"$SCRIPT_DIR/../data/test.dcm"
