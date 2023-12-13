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
set -eux pipefail
BIN_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PACKAGE_DIR="${BIN_DIR%/*}"
cd "${PACKAGE_DIR}/test"

# Note: this doesn't work as a single command
docker compose --env-file .env.test -p test up -d  --remove-orphans
cd .. && \
  docker compose --env-file test/.env.test -p test up -d --build && \
  cd "${PACKAGE_DIR}/test"

./scripts/insert_test_data.sh

pip install "${PACKAGE_DIR}/pixl_core" "${PACKAGE_DIR}/cli"
pixl populate data/test.csv
pixl start
sleep 65  # need to wait until the DICOM image is "stable" = 60s
./scripts/check_entry_in_pixl_anon.sh
./scripts/check_entry_in_orthanc_anon.sh
./scripts/check_max_storage_in_orthanc_raw.sh

cd "${PACKAGE_DIR}"
docker compose -f docker-compose.yml -f ../docker-compose.yml -p test down
docker volume rm test_postgres-data test_orthanc-raw-data test_orthanc-anon-data
