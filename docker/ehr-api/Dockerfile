FROM python:3.10.6-slim-bullseye
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends procps ca-certificates \
    iproute2 git curl libpq-dev curl gnupg g++ locales
RUN sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
RUN  apt-get autoremove && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app

ENV VIRTUAL_ENV=/app/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY ./pixl_ehr/src/requirements.txt .
RUN pip install --no-cache-dir -U pip wheel setuptools \
    && pip install --no-cache-dir -r requirements.txt

RUN mkdir local_deps
COPY ./token_buffer/src/ local_deps/token_buffer/
COPY ./pixl_rd/src/ local_deps/pixl_rd/
RUN for dir in local_deps/*/; do pip install --no-cache-dir -r "${dir}requirements.txt" $dir; done


COPY ./pixl_ehr/src ./pixl_ehr
RUN pip install --no-cache-dir ./pixl_ehr

HEALTHCHECK CMD /usr/bin/curl -f http://0.0.0.0:8000/heart-beat || exit 1

WORKDIR /app/pixl_ehr
ENTRYPOINT ["uvicorn", "pixl_ehr.main:app", "--host", "0.0.0.0", "--port", "8000"]
