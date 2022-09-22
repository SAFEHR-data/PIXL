FROM ubuntu:focal
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]

ARG HTTP_PROXY
ARG http_proxy
ARG HTTPS_PROXY
ARG https_proxy

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends \
        apt-utils apt-transport-https lsb-release procps less ca-certificates git \
        dirmngr software-properties-common libpq-dev build-essential gnupg iputils-ping \
        python3.8-dev python3-venv python3-pip \
        libv8-dev libzmq3-dev libcurl4-openssl-dev libssl-dev curl locales sudo && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 1
RUN sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /sandbox/
RUN pip install -U pip wheel setuptools \
    && pip install --timeout 120 --retries 10 --no-cache-dir -r /sandbox/requirements.txt

WORKDIR /sandbox/
ADD . /sandbox/
