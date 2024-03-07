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
FROM orthancteam/orthanc:24.3.1
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]
# need some packages for building python 3.9.13
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt update \
    && apt install --yes --no-install-recommends \
           build-essential \
           libbz2-dev \
           libffi-dev \
           libgdbm-dev \
           libncurses5-dev \
           libnss3-dev \
           libreadline-dev \
           libsqlite3-dev \
           libssl-dev \
           zlib1g-dev \
    && apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Default for Debian Bullseye (11) is python 3.9.2, which has a bug in ftplib that is
# affecting us.
# See https://bugs.python.org/issue43285 for more details. It only happens in the system
# test, when docker is using NAT to implement host.docker.internal
# Install 3.9.13 alongside the existing version (removing the original python beforehand
# seems to break orthanc)
ADD https://www.python.org/ftp/python/3.9.13/Python-3.9.13.tgz /python3913/
RUN cd /python3913 \
    && tar -xvf Python-3.9.13.tgz \
    && cd Python-3.9.13 \
    && ./configure --enable-optimizations \
    && make -j `nproc` \
    && make install \
    && make clean \
    && rm -fr /python3913

# Install requirements before copying modules
COPY ./pixl_core/pyproject.toml ./pixl_core/pyproject.toml
COPY ./pixl_dcmd/pyproject.toml ./pixl_dcmd/pyproject.toml
RUN --mount=type=cache,target=/root/.cache \
    pip3 install pixl_core/ \
    && pip3 install pixl_dcmd/

COPY ./orthanc/orthanc-anon/plugin/pixl.py /etc/orthanc/pixl.py

COPY ./pixl_core/ ./pixl_core
RUN --mount=type=cache,target=/root/.cache \
    pip3 install ./pixl_core

COPY ./pixl_dcmd/ ./pixl_dcmd
RUN --mount=type=cache,target=/root/.cache \
    pip3 install ./pixl_dcmd
