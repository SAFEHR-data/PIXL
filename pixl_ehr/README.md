# PIXL Electronic Health Record Extractor

This service has an exposed HTTP endpoint for updating the processing rate 
of the EHR extraction from EMAP star. It also includes the processing pipeline
for transforming (inc. anonymization) the data and persisting it in the PIXL 
postgres database.

## Installation

```bash
pip install -e ../pixl_core/ .
python -m spacy download en_core_web_lg  # Download spacy language model for deidentification
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
