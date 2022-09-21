#!/usr/bin/env bash

set -eo pipefail

BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${BIN_DIR%/*}"

cd $PROJECT_DIR

docker compose config --quiet

hasher/src/bin/run-tests.sh
