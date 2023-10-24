# PIXL PACS Extractor

The picture archiving and communication system (PACS) extraction API is 
identical in structure to the [EHR API](../pixl_ehr/README.md) but includes 
different processing to transfer DICOM studies from the VNA to the "raw" 
Orthanc instance, from which the anonymisation and push over DICOMWeb to 
are automatic.

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
