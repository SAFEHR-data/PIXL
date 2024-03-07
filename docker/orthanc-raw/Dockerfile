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
FROM orthancteam/orthanc:24.3.3
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]

ARG ORTHANC_RAW_MAXIMUM_STORAGE_SIZE

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends python3-venv

# Install requirements before copying modules
COPY ./pixl_core/pyproject.toml /pixl_core/pyproject.toml
COPY ./pixl_dcmd/pyproject.toml /pixl_dcmd/pyproject.toml

RUN --mount=type=cache,target=/root/.cache \
    pip3 install pixl_core/ \
    && pip3 install pixl_dcmd/

COPY ./pixl_core/ ./pixl_core
RUN --mount=type=cache,target=/root/.cache \
    pip3 install ./pixl_core

COPY ./pixl_dcmd/ ./pixl_dcmd
RUN --mount=type=cache,target=/root/.cache \
    pip3 install ./pixl_dcmd

COPY ./orthanc/orthanc-raw/plugin/pixl.py /etc/orthanc/pixl.py

# Orthanc can't substitute environment veriables as integers so copy and replace before running
COPY ./orthanc/orthanc-raw/config /run/secrets
RUN sed -i "s/\${ORTHANC_RAW_MAXIMUM_STORAGE_SIZE}/${ORTHANC_RAW_MAXIMUM_STORAGE_SIZE:-0}/g" /run/secrets/orthanc.json
