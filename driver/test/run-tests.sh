#!/usr/bin/env bash
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
set -euxo pipefail

THIS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PACKAGE_DIR="${THIS_DIR%/*}"
cd "$PACKAGE_DIR" || exit

pip install -r src/requirements.txt

CONF_FILE=../setup.cfg
mypy --config-file ${CONF_FILE} src/pixl_driver
isort --settings-path ${CONF_FILE} src/pixl_driver
black src/pixl_driver
flake8 --config ${CONF_FILE}

export ENV="test"

docker compose --env-file .env.test up queue -d
docker compose --env-file .env.test up driver

set -a  # Export all the variables in .env.test
source ./.env.test
set +a

pytest

docker compose --env-file .env.test down
