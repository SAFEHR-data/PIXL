# Project-based study routing

* Status: accepted
* Deciders: Stef Piatek, Paul Smith
* Date: 2024-11-27

Technical Story: [PIXL can take multiple projects](https://github.com/SAFEHR-data/PIXL/issues/330)

## Context and Problem Statement

Each study sent to `orthanc-anon` needs to be de-identified using the project-specific configuration. 
We need a way to pass along this information along with the DICOM file.

## Considered Options

* DICOM tag: Adding a custom DICOM tag for the project name
* custom REST API endpoint: Creating a custom REST API endpoint for `orthanc-anon` to pull the data from `orthanc-raw`

## Decision Outcome

Chosen option: "custom REST API endpoint", because the project tag updating was causing `orthanc-raw` to crash,
and we were no longer using study stability to control export.

## Pros and Cons of the Options <!-- optional -->

### DICOM tag

Add private creator group to instances as they arrive, and a dummy value in the custom tag. 
Once the study has been pulled from the DICOM source, update the tag with the filename stem of the project config.

* Good, because you can see which study was most recently exported
* Bad, `orthanc-raw` started crashing when updating the DICOM tag via the orthanc API on large studies
* Bad, because we were having to update the DICOM tag without changing the instance UIDs. 
  So that we can check for missing instances for studies which already exist in `orthanc-raw`
* Bad, studies appeared where instances didn't have their custom DICOM tag updates
* Bad, could have a race condition where the same study is trying to be exported by two projects

### Custom REST API endpoint

Once the study has been pulled from the DICOM source, send a REST request to `orthanc-anon` with the study UID and project.
`orthanc-anon` then adds this job to a threadpool and returns a 200 status to the client. 

* Good, keeping original instances unaltered
* Good, thread-pooling allows for faster de-identification
* Good, simpler flow
* Bad, we can't alter the queue of de-identification jobs short of taking down `orthanc-anon`

## Links <!-- optional -->

* Related to multiple project configuration [ADR-0004](0004-multiple-project-configuration.md)
