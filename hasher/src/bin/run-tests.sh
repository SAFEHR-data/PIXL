#!/usr/bin/env bash

set -eo pipefail

BIN_DIR=$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)
HASHER_DIR="${BIN_DIR%/*}"
cd $HASHER_DIR

CONF_FILE=../../setup.cfg


mypy --config-file ${CONF_FILE} hasher

isort --settings-path ${CONF_FILE} hasher

black hasher

flake8 --config ${CONF_FILE}

PIXL_ENV=test pytest hasher/tests
