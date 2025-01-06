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
FROM python:3.12.4-slim-bullseye@sha256:26ce493641ad3b1c8a6202117c31340c7bbb2dc126f1aeee8ea3972730a81dc6 AS pixl_python_base
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]

ARG TEST="false"

RUN <<EOF
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends \
        procps \
        ca-certificates \
        iproute2 \
        libpq-dev \
        curl \
        gnupg \
        locales \
        tzdata && \
    sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && locale-gen && \
    apt-get autoremove --yes && apt-get clean --yes && rm -rf /var/lib/apt/lists/*
EOF

HEALTHCHECK CMD /usr/bin/curl -f http://0.0.0.0:8000/heart-beat || exit 1

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.10 /uv /uvx /bin/

WORKDIR /app
# specify what we're installing using build time arg
ARG PIXL_PACKAGE_DIR

# Install our code:

# COPY doesn't support a wildcard copy which also preserves directory structure,
# so we have to specify everything separately. We could have copied everything, but
# then every change would trigger a rebuild of all containers.

# The workspace project file
COPY pyproject.toml .
# All pyproject.toml files referenced by the root one must exist or uv will error
COPY ./pixl_imaging/pyproject.toml pixl_imaging/pyproject.toml
COPY ./pixl_export/pyproject.toml pixl_export/pyproject.toml
COPY ./pixl_dcmd/pyproject.toml pixl_dcmd/pyproject.toml
COPY ./cli/pyproject.toml cli/pyproject.toml
COPY ./hasher/pyproject.toml hasher/pyproject.toml
# prereqs for all projects
COPY ./pytest-pixl/ pytest-pixl/
COPY ./pixl_core/ pixl_core/
# the actual thing we are building
COPY ./$PIXL_PACKAGE_DIR/ $PIXL_PACKAGE_DIR/
RUN uv venv
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked uv sync --package "$PIXL_PACKAGE_DIR"

# make uvicorn etc available
ENV PATH="/app/.venv/bin:$PATH"

# Each container should be run with a different entry point
FROM pixl_python_base AS export_api
ENTRYPOINT ["uvicorn", "pixl_export.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM pixl_python_base AS hasher_api
ENTRYPOINT ["uvicorn", "hasher.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM pixl_python_base AS imaging_api
ENTRYPOINT ["/app/pixl_imaging/scripts/migrate_and_run.sh"]
