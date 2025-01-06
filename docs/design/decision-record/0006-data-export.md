# Export of parquet files and DICOM data

* Status: accepted
* Deciders: Haroon Chughtai, Jeremy Stein, Milan Malfait, Ruaridh Gollifer, Stef Piatek
* Date: 2024-02-26

## Context and Problem Statement

The pipeline needs to be able to export DICOM images and structured data files to different endpoints. 

## Decision Drivers <!-- optional -->

* We expect that some projects will have more data than we can store locally. Will need a rolling export of images
* We will need to be able to export images and structured data via FTPS in an automated fashion
* We will need to be able to export images via DICOMWeb


## Considered Options

* Shared python library for exporting of data, used in `orthanc-anon` and the `pixl` CLI.
* `export-api` service, which can export both DICOM and structured data files. 

## Decision Outcome

Chosen options: "`export-api` service", for clear separation of responsibilities.

## Pros and Cons of the Options <!-- optional -->

### Shared python library

Add private creator group to instances as they arrive, and a dummy value in the custom tag.
Once the study has been pulled from the DICOM source, update the tag with the filename stem of the project config.

* Good, one less service to maintain
* Good, export via DICOMWeb is using the orthanc API already
* Bad, duplication of implementation for export
* Bad, duplication of areas where secrets are used

### `export-api` service

Instead of shared library the code would be in the service alone. 

* Good, single service that will access all secrets and orchestrate exports
* Good, allows caching of export secrets in a long-running service
* Bad, would require extra code for interacting with the service from the CLI for parquet export
