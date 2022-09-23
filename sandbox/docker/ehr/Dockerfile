FROM python:3.10.7-slim-bullseye
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]

ARG HTTP_PROXY
ARG http_proxy
ARG HTTPS_PROXY
ARG https_proxy

# OS setup
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends procps ca-certificates \
    iproute2 git curl libpq-dev gnupg g++ locales postgresql-client
RUN sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && locale-gen


 # clean up
RUN  apt-get autoremove && apt-get clean && rm -rf /var/lib/apt/lists/*

# Directory setup
RUN mkdir /app
WORKDIR /app

ENV VIRTUAL_ENV=/app/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt /sandbox/
RUN pip install -U pip wheel setuptools \
    && pip install --timeout 120 --retries 10 --no-cache-dir -r /sandbox/requirements.txt

WORKDIR /sandbox/
ADD . /sandbox/
