#!/bin/bash
set -o nounset

psql -U "${POSTGRES_USER}" -tc "SELECT 1 FROM pg_database WHERE datname = '${PIXL_DB_NAME}'" |\
    grep -q 1 | \
    psql -U "${POSTGRES_USER}" -c "CREATE DATABASE ${PIXL_DB_NAME}"

# Create the EHR schema and associated tables
ehr_create_command="CREATE SCHEMA emap_data AUTHORIZATION ${POSTGRES_USER}
    CREATE TABLE demographics_raw (mrn text, accession_number text, age integer, sex text, ethnicity text, height real, weight real, gcs integer)
    CREATE TABLE demographics_anon (mrn text, accession_number text, age integer, sex text, ethnicity text, height real, weight real, gcs integer)
"
psql -U "${POSTGRES_USER}" --dbname "${PIXL_DB_NAME}" -c "$ehr_create_command"
