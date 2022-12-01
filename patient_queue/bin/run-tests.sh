#!/usr/bin/env bash

#
# Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

set -eo pipefail

BIN_DIR=$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)
QUEUE_DIR="${BIN_DIR%/*}"
cd $QUEUE_DIR || exit

echo $PWD

docker compose -f ./bin/docker-compose.yml build
docker compose -f ./bin/docker-compose.yml up -d
docker exec pixl-test-python /bin/bash -c "pytest /patient_queue/patient_queue/tests/tests_producer.py"
# docker exec pixl-test-python /bin/bash -c "pytest /patient_queue/patient_queue/tests/tests_subscriber.py"
docker compose -f ./bin/docker-compose.yml down
