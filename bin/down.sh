#!/usr/bin/env bash

set -o errexit -o pipefail -o noclobber


BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${BIN_DIR%/*}"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"

exec docker compose -f ${COMPOSE_FILE} down "${@}"
