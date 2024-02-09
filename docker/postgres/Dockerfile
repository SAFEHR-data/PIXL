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
FROM postgres:16-bookworm

# OS setup
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends procps ca-certificates locales python3 python3-pip python3.11-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

COPY --chmod=0755 ./postgres/postgres.conf /etc/postgresql/postgresql.conf

COPY --chmod=0777 ./postgres/pixl-db_init.sh /docker-entrypoint-initdb.d/pixl-db_init.sh

COPY --chmod=0777 ./postgres/create_pixl_tbls.py /pixl/create_pixl_tbls.py

# Install requirements before copying modules
COPY ./pixl_core/pyproject.toml /pixl/pixl_core/pyproject.toml
RUN --mount=type=cache,target=/root/.cache \
    python3 -m venv /pixl/venv \
        && cd /pixl/venv/bin \
        && ./pip install /pixl/pixl_core/

WORKDIR /pixl/venv/bin

COPY ./pixl_core/ /pixl/pixl_core

RUN --mount=type=cache,target=/root/.cache \
    ./pip install /pixl/pixl_core/
