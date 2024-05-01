# PIXL Export API

The Export API provides HTTP endpoints to control the copying of EHR data from the OMOP extract
to its destination (eg. FTPS). It also uploads DICOM data to its destination after it has been
processed by the Imaging API and orthanc(s).
It no longer accepts messages from rabbitmq.

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
pip install -e ../pixl_core/ -e .
```

## Test

```bash
pip install -e ../pixl_core/ -e .[test]
pytest
```

## Usage

Usage should be from the CLI driver, which calls the HTTP endpoints.

## Notes

- The height/weight/GCS value is extracted only within a 24 h time window
