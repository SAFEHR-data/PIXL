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
FROM postgres:14-bullseye

# OS setup
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends procps ca-certificates locales build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

ADD https://www.python.org/ftp/python/3.10.13/Python-3.10.13.tgz /pixl/python/

RUN cd /pixl/python/ && \
    tar -xvf Python-3.10.13.tgz && \
    cd Python-3.10.13 && \
    ./configure --enable-optimizations && \
    make -j 2 && \
    make altinstall

COPY --chmod=0755 ./postgres/postgres.conf /etc/postgresql/postgresql.conf

COPY --chmod=0777 ./postgres/pixl-db_init.sh /docker-entrypoint-initdb.d/pixl-db_init.sh

COPY ./postgres/create_pixl_tbls.py /pixl/create_pixl_tbls.py

COPY ./pixl_core/ /pixl/pixl_core

RUN python3.10 -m pip install /pixl/pixl_core/
