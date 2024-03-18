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
insert into star.mrn(mrn_id, mrn, research_opt_out) values (1234, '12345678', false);
insert into star.mrn(mrn_id, mrn, research_opt_out) values (2345, '987654321', false);
insert into star.mrn(mrn_id, mrn, research_opt_out) values (3456, '5020765', false);
insert into star.core_demographic(mrn_id, date_of_birth, sex, ethnicity) values (1234, '1901-01-01', 'F', 'testethnicity1');
insert into star.core_demographic(mrn_id, date_of_birth, sex, ethnicity) values (2345, '1901-01-01', 'F', 'testethnicity2');
insert into star.core_demographic(mrn_id, date_of_birth, sex, ethnicity) values (3456, '1901-01-01', 'F', 'testethnicity3');

insert into star.lab_sample(lab_sample_id, external_lab_number, mrn_id) values (45671, 'AA12345601', 2345);
insert into star.lab_sample(lab_sample_id, external_lab_number, mrn_id) values (45672, 'AA12345605', 2345);
insert into star.lab_order(lab_order_id, lab_sample_id) values (56781, 45671);
insert into star.lab_order(lab_order_id, lab_sample_id) values (56782, 45672);

insert into star.lab_test_definition(lab_test_definition_id, test_lab_code) values (6789, 'NARRATIVE');

insert into star.lab_result(lab_result_id, lab_order_id, lab_test_definition_id, value_as_text)
    VALUES (78901, 56781, 6789, 'this is a radiology report 1');
insert into star.lab_result(lab_result_id, lab_order_id, lab_test_definition_id, value_as_text)
    VALUES (78902, 56782, 6789, 'this is a radiology report 2');
"

docker exec system-test-fake-star-db /bin/bash -c "psql -U postgres -d emap -c \"$_sql_command\""

# Uses an accession number of "AA12345601" for MRN 987654321
curl -X POST -u "orthanc:orthanc" "http://localhost:8043/instances" \
  --data-binary @"$SCRIPT_DIR/../resources/Dicom1.dcm"
# Uses an accession number of "AA12345605"  for MRN 987654321, already has project name added
# Send to orthanc raw to ensure that we can resend an existing message without querying VNA again
curl -X POST -u "orthanc_raw_username:orthanc_raw_password" "http://localhost:7005/instances" \
  --data-binary @"$SCRIPT_DIR/../resources/Dicom2.dcm"
