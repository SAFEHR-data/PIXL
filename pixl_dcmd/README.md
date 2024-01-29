# PIXL DICOM de-identifier

This module includes the processing pipeline for transforming (inc. anonymization) the data 
and persisting it in the PIXL postgres database.

## Installation

Install the Python dependencies with

```bash
pip install -e ../pixl_core/ .[test,dev]
```

## Test

```bash
pytest
```
