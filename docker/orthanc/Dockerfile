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
FROM orthancteam/orthanc:24.7.3@sha256:57a3d037729897331027ddc00c12695b50f1effbbf805f855396f3d0248d2d5f AS pixl_orthanc_uv
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]

# Create a virtual environment, recommended since python 3.11 and Debian bookworm based images
# where you get a warning when installing system-wide packages.
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends curl tzdata && \
    apt-get autoremove --yes && apt-get clean --yes && rm -rf /var/lib/apt/lists/*

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.10 /uv /uvx /bin/
ENV PYTHONPATH=/.venv/lib64/python3.11/site-packages/

FROM pixl_orthanc_uv AS pixl_orthanc_with_spec
# This part changes rarely, so do it nice and early to avoid redoing it every time we change our code.
# It does have a dependency though, which would normally be fulfilled by our project files, so install that
# manually.
# Do it in dead end build stage to discard this environment afterwards,
# and because the spec is only needed in orthanc-anon.
RUN uv venv
RUN uv pip install dicom-validator==0.7.3
COPY ./orthanc/orthanc-anon/plugin/download_dicom_spec.py /etc/orthanc/download_dicom_spec.py
RUN --mount=type=cache,target=/root/.cache,id=dlspec \
    python3 /etc/orthanc/download_dicom_spec.py


FROM pixl_orthanc_uv AS pixl_orthanc_base
# Install our code
# The workspace (root-level) project file
COPY pyproject.toml .
# All pyproject.toml files referenced by the root one must exist or uv will error
COPY ./pixl_imaging/pyproject.toml pixl_imaging/pyproject.toml
COPY ./pixl_export/pyproject.toml pixl_export/pyproject.toml
COPY ./cli/pyproject.toml cli/pyproject.toml
COPY ./hasher/pyproject.toml hasher/pyproject.toml
# prereqs for dcmd
COPY ./pytest-pixl/ pytest-pixl/
COPY ./pixl_core/ pixl_core/
COPY ./pixl_dcmd/ pixl_dcmd
RUN uv venv
# Need --no-editable so that our packages are in
# site-packages, so orthanc plugin manager can find them
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked uv sync --no-editable --package pixl-dcmd

ARG ORTHANC_DIR
COPY ./orthanc/${ORTHANC_DIR}/plugin/pixl.py /etc/orthanc/pixl.py
COPY ./orthanc/${ORTHANC_DIR}/config /run/secrets


# Orthanc can't substitute environment veriables as integers so copy and replace before running
ARG ORTHANC_CONCURRENT_JOBS
RUN sed -i "s/\${ORTHANC_CONCURRENT_JOBS}/${ORTHANC_CONCURRENT_JOBS:-5}/g" /run/secrets/orthanc.json

FROM pixl_orthanc_base AS pixl_orthanc_raw

ARG ORTHANC_RAW_MAXIMUM_STORAGE_SIZE
ARG ORTHANC_RAW_JOB_HISTORY_SIZE
ARG PIXL_DICOM_TRANSFER_TIMEOUT
RUN sed -i "s/\${ORTHANC_RAW_MAXIMUM_STORAGE_SIZE}/${ORTHANC_RAW_MAXIMUM_STORAGE_SIZE:-0}/g" /run/secrets/orthanc.json
RUN sed -i "s/\${ORTHANC_RAW_JOB_HISTORY_SIZE}/${ORTHANC_RAW_JOB_HISTORY_SIZE:-100}/g" /run/secrets/orthanc.json
RUN sed -i "s/\${ORTHANC_RAW_STABLE_SECONDS}/${PIXL_DICOM_TRANSFER_TIMEOUT:-600}/g" /run/secrets/orthanc.json

FROM pixl_orthanc_base AS pixl_orthanc_anon
COPY --from=pixl_orthanc_with_spec /root/dicom-validator /root/dicom-validator
