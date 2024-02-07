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
FROM osimis/orthanc:22.9.0-full-stable
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]

# python3-venv required for piptools
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends python3-venv
RUN sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
RUN  apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*


# Install requirements before copying modules
RUN --mount=type=cache,target=/root/.cache\
    pip install pip-tools
COPY ./pixl_core/pyproject.toml pyproject.toml
COPY ./pixl_dcmd/pyproject.toml dcmd.toml


RUN --mount=type=cache,target=/root/.cache \
    && python3 -m piptools compile --max-rounds 1 pyproject.toml -o core.txt \
    && pip3 install -r core.txt \
    && python3 -m piptools compile --max-rounds 1 dcmd.toml -o dcmd.txt \
    && pip3 install -r dcmd.txt

COPY ./orthanc/orthanc-anon/plugin/pixl.py /etc/orthanc/pixl.py
COPY ./orthanc/orthanc-anon/plugin/tag-operations.yaml /etc/orthanc/tag-operations.yaml

COPY ./pixl_core/ ./pixl_core
RUN pip3 install --no-cache-dir ./pixl_core

COPY ./pixl_dcmd/ ./pixl_dcmd
RUN pip3 install --no-cache-dir ./pixl_dcmd