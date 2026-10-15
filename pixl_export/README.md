# PIXL Export API

The Export API provides HTTP endpoints to control the copying of EHR data from the OMOP extract
to its destination (eg. FTPS). It also uploads DICOM data to its destination after it has been
processed by the Imaging API and orthanc(s).
It no longer accepts messages from rabbitmq.

## Installation

In production, the Export API runs in a Docker container (`export-api`) started by `uv run pixl dc up`,
so it does not need to be installed on the host.

For local development and testing, this module is installed along with the rest of PIXL. See the
[developer setup instructions](../docs/setup/developer.md#installation-of-pixl-modules).

## Test

```bash
uv run pytest
```

## Usage

Usage should be from the CLI driver, which calls the HTTP endpoints.
