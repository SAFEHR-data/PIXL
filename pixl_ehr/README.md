# PIXL Electronic Health Record Extractor

This service has an exposed HTTP endpoint for updating the processing rate 
of the EHR extraction from EMAP star. It also includes the processing pipeline
for transforming (inc. anonymization) the data and persisting it in the PIXL 
postgres database.

## Installation

```bash
pip install ../pixl_core/ .
```

## Test

```bash
pip install -e ../pixl_core/[test] .[test]
pytest -m "not processing"
```
or the full set with
```bash
cd tests
docker compose up -d --build
docker exec pixl-test-ehr-api /bin/bash -c "pytest pixl_ehr/"
docker compose down
```

## Usage

Usage should be from the CLI driver, which calls the HTTP endpoints.

## Notes

- The height/weight/GCS value is extracted only within a 24 h time window
