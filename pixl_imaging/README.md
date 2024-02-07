# PIXL Imaging API

The PIXL imaging API processes messages from the imaging queue created by the [CLI](../cli/README.md) 
to query images from the [VNA](https://en.wikipedia.org/wiki/Vendor_Neutral_Archive) and transfers them to the [`orthanc-raw` instance](../orthanc/orthanc-raw/README.md).
It is identical in structure the [EHR API](../pixl_ehr/README.md).

It exposes a single HTTP endpoint that expects a JSON-formatted message structured as defined by the
[`Message`](../pixl_core/src/core/patient_queue/message.py) class in `pixl_core/patient_queue`.
On arrival of the input message it will issue a DICOMWeb request to `orthanc-raw`, which then queries the VNA
for the requested imaging study, if it didn't already exist.

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
