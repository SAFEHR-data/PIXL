# PIXL Electronic Health Record Extractor

This service has an exposed HTTP endpoint for updating the processing rate
of the EHR extraction from EMAP star. It also includes the processing pipeline
for transforming (inc. anonymization) the data and persisting it in the PIXL
postgres database.

## Installation

First, make sure you have `postgresql` installed on your system.

On macOS:

```bash
brew install postgresql
```

On Ubuntu:

```bash
sudo apt install postgresql
```

On Windows, follow [these instructions](https://www.postgresqltutorial.com/postgresql-getting-started/install-postgresql/).

Then install the Python dependencies with

```bash
pip install -e ../pixl_core/ .
```

## Test

```bash
pip install -e ../pixl_core/[test] .[test]
pytest -m "not processing"
```
and the processing tests with
```bash
./tests/run-processing-tests.sh
```

## Usage

Usage should be from the CLI driver, which calls the HTTP endpoints.

## Notes

- The height/weight/GCS value is extracted only within a 24 h time window
