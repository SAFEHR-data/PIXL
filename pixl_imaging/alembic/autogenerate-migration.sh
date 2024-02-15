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
cd "$(dirname "${BASH_SOURCE[0]}")" && pwd

# Set env variables
export PIXL_DB_HOST=localhost
export PIXL_DB_PORT=7654
export POSTGRES_PORT=${PIXL_DB_PORT}
export PIXL_DB_USER=pixl_db_username
export PIXL_DB_PASSWORD=pixl_db_password
export PIXL_DB_NAME=pixl

# create postgres
(cd ../.. && \
  docker compose -p migration-test up --wait -d --build postgres)

# run current migrations
alembic upgrade head

# generate new migrations
alembic revision --autogenerate

# take containers down
(cd ../.. && docker compose -f docker-compose.yml --env-file test/.env -p migration-test down --volumes )