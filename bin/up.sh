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
set -o errexit -o pipefail -o noclobber

ALLOWED_PROJECT_NAMES="pixl_dev, pixl_test, pixl_prod"
BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${BIN_DIR%/*}"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"

PROJECT_NAME=$1
shift;  # pop the first item from the list of arguments

if echo "${ALLOWED_PROJECT_NAMES}" | grep -v -q "${PROJECT_NAME}"; then
  echo "Cannot up services with ${PROJECT_NAME} as a project name. Must be one of: ${ALLOWED_PROJECT_NAMES}"
  exit 1
fi

exec docker compose \
  -f "${COMPOSE_FILE}" \
  --project-name "${PROJECT_NAME}" \
  up --remove-orphans --abort-on-container-exit --build \
  "${@}"
