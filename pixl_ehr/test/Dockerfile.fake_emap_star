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
# limitations under the License.
FROM postgres:15.0-bullseye

# User definable arguments
ARG POSTGRES_USER=postgres
ARG POSTGRES_PASSWORD=postgres
ARG N_TABLE_ROWS=2
ARG INFORMDB_BRANCH_NAME=develop
ARG STAR_SCHEMA_NAME=star
ARG FAKER_SEED=0
ARG TIMEZONE="Europe/London"
ARG TAG="0.0.1"

ARG DEBIAN_FRONTEND=noninteractive

# OS setup
RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
    procps ca-certificates locales python3.9-dev python3-pip git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

# Create .sql file that will be used to initallly populate the database
RUN git clone --depth 1 --branch ${TAG} https://github.com/UCLH-DIF/Satellite.git && \
    pip install --no-cache-dir --upgrade pip==22.3.1 && \
    pip install --no-cache-dir -r Satellite/requirements.txt

WORKDIR /Satellite/
RUN python3.9 print_sql_create_command.py > /docker-entrypoint-initdb.d/create.sql

# Clean up repo and Python
# hadolint ignore=DL3059
RUN rm -rf /Satellite && \
    apt-get --yes --purge autoremove python3.9 python3-pip

# Export the variables to the runtime of the container
ENV POSTGRES_USER ${POSTGRES_USER}
ENV POSTGRES_PASSWORD ${POSTGRES_PASSWORD}
ENV TIMEZONE ${TZ}
ENV LANG=en_GB.UTF-8
ENV LC_ALL=en_GB.UTF-8
