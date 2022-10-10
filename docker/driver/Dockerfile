FROM python:3.10.7-slim-bullseye
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]

# OS setup
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends procps ca-certificates \
    iproute2 git curl libpq-dev curl gnupg g++ locales
RUN sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

RUN  apt-get autoremove && apt-get clean && rm -rf /var/lib/apt/lists/*

# Directory and venv setup
RUN mkdir /driver
WORKDIR /driver

ENV VIRTUAL_ENV=/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin"

# 3rd party deps
COPY ./driver/src/requirements.txt .
RUN pip install --no-cache-dir -U pip wheel setuptools \
    && pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_lg

# driver package
COPY ./driver/src/ /driver/
RUN pip install --no-cache-dir .

ENTRYPOINT ["/bin/sleep", "infinity"]
