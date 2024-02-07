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
FROM python:3.10.6-slim-bullseye
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]

WORKDIR /core

# Install requirements before copying modules
RUN pip install pip-tools
COPY /pixl_core/pyproject.toml core.toml

RUN --mount=type=cache,target=/root/.cache \
    python -m piptools compile -o core.txt core.toml \
    && pip install -r core.txt

COPY . .
RUN pip install --no-cache-dir .[test]
