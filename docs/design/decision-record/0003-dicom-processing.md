# DICOM server and processing

* Status: accepted
* Deciders: Original PIXL team
* Date: 2023-11-01 (retrospectively)

## Context and Problem Statement

We need to have a DICOM server to query DICOM images, store them, anonymise them and export them.


## Decision Drivers <!-- optional -->

* Will need to have a robust DICOM server that has been in use
* Keep original studies in a cache locally to reduce use of clinical imaging systems if failures in anonymisation or export
* The team's lingua franca is Python
* Per-project anonymisation profiles and custom hashing of fields will require plugins to be written for anonymisation
* UCLH infrastructure allows for running docker, but we don't have admin accounts and cannot install software directly onto the machines.

## Considered Options

* XNAT server
* Orthanc server

## Decision Outcome

Chosen option: `Orthanc`, 
because it's relatively lightweight, under development and allows for python-based extensions to be written. 

## Pros and Cons of the Options <!-- optional -->

### XNAT

* Good, ARC has a history of using this in the medical imaging subgroup.
* Good, widely regarded
* Bad, heavyweight and has many more features than we need to use. May take longer to learn and deploy
* Bad, does not allow for python-based plugins to be used for anonymisation without getting into running docker in docker

### Orthanc

* Good, has been battle tested
* Good, has DICOMWeb plugin to allow for export via that modality
* Good, allows for python-based plugins and running in docker
* Bad, no previous usage within ARC. Will be teething problems
