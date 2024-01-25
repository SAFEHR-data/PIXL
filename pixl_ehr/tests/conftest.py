#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
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
from __future__ import annotations

import os

# configure environmental variables
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["RABBITMQ_PASSWORD"] = "guest"  # noqa: S105
os.environ["RABBITMQ_USERNAME"] = "guest"
os.environ["RABBITMQ_HOST"] = "queue"
os.environ["RABBITMQ_PORT"] = "5672"
os.environ["PIXL_DB_HOST"] = "localhost"
os.environ["PIXL_DB_PORT"] = "35432"
os.environ["PIXL_DB_NAME"] = "pixl"
os.environ["PIXL_DB_USER"] = "postgres"
os.environ["PIXL_DB_PASSWORD"] = "postgres"  # noqa: S105
os.environ["PIXL_DB_EHR_SCHEMA_NAME"] = "emap_data"
os.environ["EMAP_UDS_HOST"] = "localhost"
os.environ["EMAP_UDS_PORT"] = "35433"
os.environ["EMAP_UDS_NAME"] = "emap"
os.environ["EMAP_UDS_USER"] = "postgres"
os.environ["EMAP_UDS_PASSWORD"] = "postgres"  # noqa: S105
os.environ["EMAP_UDS_SCHEMA_NAME"] = "star"
os.environ["COGSTACK_REDACT_URL"] = "test"
