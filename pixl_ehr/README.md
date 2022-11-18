# PIXL Electronic Health Record Extractor

This service has an exposed HTTP endpoint for updating the processing rate 
of the EHR extraction from EMAP star. It also includes the processing pipeline
for transforming (inc. anonymization) the data and persisting it in the PIXL 
postgres database.

## Installation

Local installation is possible to run the api tests, but require installing 
all the associated PIXL pip packages found at the repo root.

## Usage

Usage should be from the CLI driver, which interacts with the endpoint.


## Notes

- The height/weight/GCS value is extracted only within a 24 h time window
