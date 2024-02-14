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

# Run migrations (unless SKIP_ALEMBIC is true) then run the app.

set -eu -o pipefail
cd /app
if [ "${SKIP_ALEMBIC:-false}" = false ]; then
    echo "Running alembic migrations"
    alembic upgrade head
else
    echo "Skipping alembic migrations"
fi

uvicorn pixl_imaging.main:app --host "0.0.0.0" --port 8000