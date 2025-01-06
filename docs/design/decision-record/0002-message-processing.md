# Message-based Processing of Images

* Status: accepted
* Deciders: Original PIXL team, most recent changes: Stef Piatek & Paul Smith
* Date: 2024-12-12

## Context and Problem Statement

- We need a way to buffer the messages awaiting processing. 
  We expect hundreds to tens of thousands of imaging studies to be requested per project, 
  and want to find each study in the source systems individually. 


## Decision Drivers <!-- optional -->

- Be able to process multiple research projects at the same time
- Should be persistent if services are taken down
- Allow for a secondary DICOM source to be used if study isn't found in the primary
- Limit the total number of images that are being processed for a given source system
- Studies that have already been successfully exported for a project should not get processed again

## Considered Options

* Use of database alone to schedule run, with the CLI driving a long-running job to process all studies in research project
* Use of queues to buffer requests that the `imaging-api` processes, database to track the status of exported studies

## Decision Outcome

Chosen option: `Queue for buffering requests, database to track status of export`, 
because it fulfills all requirements and allows us to invest in use of generic technologies.

## Pros and Cons of the Options <!-- optional -->

### Database alone


* Good, simple to set up and use. Single solution for buffering requests and tracking status
* Bad, bespoke solution where we could use a technology that can be transferrable to other situations 
* Bad, complex setup to limit total queries per source system

### Queue with database for status


* Good, fulfills all requirements fairly easily, creating a queue for primary and another for secondary imaging sources
* Good, because we have previously invested in rabbitmq as a technology
* Bad, extra services to manage and extra development
* Bad, because original implementation was broken and required effort to fix. Though we learned more about the libraries we're using.
