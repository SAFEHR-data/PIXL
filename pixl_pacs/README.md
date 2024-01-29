# PIXL Imaging API

The PIXL imaging API provides an HTTP endpoint to extract images from the [VNA]() to the [`orthanc-raw` instance](../orthanc/orthanc-raw/README.md).
It is identical in structure the [EHR API](../pixl_ehr/README.md).

## Installation

```bash
pip install -e ../pixl_core/ .
```

## Test

```bash
./tests/run-tests.sh
```

## Usage

Usage should be from the CLI driver, which interacts with the endpoint.
