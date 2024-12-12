# Multiple-project configuration

* Status: accepted
* Deciders: Milan Malfait, Peter Tsrunchev, Jeremy Stein,  Stef Piatek
* Date: 2024-03-05

Technical Story: [PIXL can take multiple projects](https://github.com/SAFEHR-data/PIXL/issues/330)

## Context and Problem Statement

Each project should be able to define its own anonymisation profile and export destinations.

## Decision Drivers <!-- optional -->

* When hashing a given field for an imaging study for two different projects, each project's hash should be different.
  This it to avoid inappropriate linkage of data between research projects. 
* Secure storage of secrets, especially for connection to destinations and per-project hashing salts

## Considered Options

* file-based: env files for docker or structured files for secrets 
* self-hosted secret storage service
* azure keyvault

## Decision Outcome

Chosen option: "azure keyvault", because its low hassle and gives us good control of secret access.

### Positive Consequences <!-- optional -->

* Single place for secrets, which multiple deployments can access
* Can have secrets which expire, so even if compromised we limit the amount of secret leakage possible
* Per-project salts stored in a separate keyvault than the export endpoints
* Only need to define the destination type, with the keyvalut defining all the connection details

### Negative Consequences <!-- optional -->

* Requires other implementations to set up their own azure storage accounts or develop new secret management
* Developers also have to update a `.env` file for running the system test
* Slight increase in cost, can be slightly offset by caching credentials 

## Pros and Cons of the Options <!-- optional -->

### File-based

* Good, simple to do
* Bad, will keep on expanding as time goes on which can be a pain to maintain
* Bad, no access control beyond unix permissions

### Self-hosted secret storage

* Good, fine-grained access control possible
* Good, free in terms of upfront cost
* Bad, another service to maintain - residual costs

### Azure keyvault

[example | description | pointer to more information | …] <!-- optional -->

* Good, fine-grained access control possible
* Bad, slight increase in cost

## Links <!-- optional -->

* Routing of studies based on projects in [ADR-0005](0005-project-based-study-routing.md) 
