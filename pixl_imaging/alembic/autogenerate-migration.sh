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

if [ $# -ne 1 ]
  then
    echo "Add a name for the migration in quotes"
    exit 1
fi

export PIXL_DB_HOST=localhost

# create postgres
(cd ../.. && \
  docker compose --env-file test/.env -p migration-test up  --wait -d --build postgres)

# run current migrations
alembic upgrade head

# generate new migrations
alembic revision --autogenerate -m "$1"

# take containers down
(cd ../.. && docker compose --env-file test/.env -p migration-test down --volumes )