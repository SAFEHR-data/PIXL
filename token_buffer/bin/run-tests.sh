#!/usr/bin/env bash
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
set -eo pipefail

BIN_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PACKAGE_DIR="${BIN_DIR%/*}"
cd "$PACKAGE_DIR"

CONF_FILE=../setup.cfg
mypy --config-file ${CONF_FILE} src/token_buffer
isort --settings-path ${CONF_FILE} src/token_buffer
black src/token_buffer
flake8 --config ${CONF_FILE} src/token_buffer

ENV=test pytest src/token_buffer/tests
