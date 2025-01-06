# Multi-service Architecture

* Status: accepted
* Deciders: Original PIXL team
* Date: 2023-11-01 (retrospectively)

## Context and Problem Statement

We want a software solution that has distinct functionality. How do we structure those services.

## Decision Drivers <!-- optional -->

* Will need to allow for concurrent processing of tasks
* Lingua franca of the team is python

## Considered Options

* Multi-service architecture
* Monolith architecture

## Decision Outcome

Chosen option: "Multi-service architecture", because it allows us to:

- Break up our code into logical packages and services
- Get around a single python process being blocked by the global interpreter lock, as each service runs in its own process
- Forces us to consider where code should go, and restrict services from using other services code
- Works well with UCLH's restriction to deploy services using docker and docker compose, open to extend into kubernetes should we want that
