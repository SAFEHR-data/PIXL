# PIXL Imaging API

The PIXL imaging API processes messages from the imaging queue created by the [CLI](../cli/README.md) 
to query images from the [VNA]() and transfers them to the [`orthanc-raw` instance](../orthanc/orthanc-raw/README.md).
It is identical in structure the [EHR API](../pixl_ehr/README.md).

It exposes a single HTTP endpoint that expects a JSON-formatted message structured as defined by the
[`Message`](../pixl_core/src/core/patient_queue/message.py) class in `pixl_core/patient_queue`.

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
