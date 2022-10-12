#!/bin/bash

psql -U ${POSTGRES_USER} -tc "SELECT 1 FROM pg_database WHERE datname = '${PIXL_DB_NAME}'" |\
    grep -q 1 | \
    psql -U ${POSTGRES_USER} -c "CREATE DATABASE ${PIXL_DB_NAME}"
