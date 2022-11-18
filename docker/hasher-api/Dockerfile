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
FROM python:3.10.7-slim-bullseye
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]


# OS setup
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends procps ca-certificates \
    iproute2 git curl libpq-dev curl gnupg g++ locales
RUN sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

 # clean up
RUN  apt-get autoremove && apt-get clean && rm -rf /var/lib/apt/lists/*

# Directory setup
RUN mkdir /app
WORKDIR /app

ENV VIRTUAL_ENV=/app/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 3rd party deps
COPY ./hasher/src/requirements.txt .
RUN pip install --no-cache-dir -U pip wheel setuptools \
    && pip install --no-cache-dir -r requirements.txt

# hasher
COPY ./hasher/src ./hasher
RUN pip install --no-cache-dir ./hasher

WORKDIR /app/hasher
ENTRYPOINT ["uvicorn", "hasher.main:app", "--host", "0.0.0.0", "--port", "8000"]
