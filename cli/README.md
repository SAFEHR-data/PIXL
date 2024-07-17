# PIXL Driver + Command line interface

The PIXL CLI driver provides functionality to populate a queue with messages containing information
required to run electronic health queries against the EMAP star database and the VNA image system.
Once a set of queues are populated the consumers can be started, updated and the system extractions
stopped cleanly.

## Prerequisites

`PIXL CLI` requires Python version 3.10.

Running the tests requires [docker](https://docs.docker.com/get-docker/) to be installed.

## Installation

We recommend installing in a project specific virtual environment created using a environment
management tool such as [conda](https://docs.conda.io/en/latest/) or
[virtualenv](https://virtualenv.pypa.io/en/latest/).

Then install in editable mode by running

```bash
python -m pip install -e ../pixl_core/ -e .
```

## Usage

**Note** The `rabbitmq`, `export-api` and `imaging-api` services must be started prior to using the CLI
This is done by spinning up the necessary Docker containers through `docker compose`.
For convenience, we provide the `pixl dc` command, which acts as a wrapper for `docker compose`,
but takes care of some of the configuration for you.

See the commands and subcommands with

```bash
pixl --help
```

### Configuration

The `rabbitmq` and `postgres` services are configured by setting the following environment variables
(default values shown):

```sh
RABBITMQ_HOST=localhost
RABBITMQ_PORT=7008
RABBITMQ_USERNAME=rabbitmq_username
RABBITMQ_PASSWORD=rabbitmq_password

POSTGRES_HOST=localhost
POSTGRES_PORT=7001
PIXL_DB_USER=pixl_db_username
PIXL_DB_PASSWORD=pixl_db_password
PIXL_DB_NAME=pixl
```

The `rabbitmq` queues for the `imaging` API is configured by setting:

```sh
PIXL_IMAGING_API_HOST=localhost
PIXL_IMAGING_API_PORT=7007
PIXL_IMAGING_API_RATE=1
```

where the `*_RATE` variables set the default querying rate for the message queues.

### Running the pipeline

Populate queue for Imaging

```bash
pixl populate </path/to/parquet_dir>
```

where `parquet_dir` contains at least the following files:

```sh
parquet_dir
├── extract_summary.json
├── private
│   ├── PERSON_LINKS.parquet
│   └── PROCEDURE_OCCURRENCE_LINKS.parquet
└── public
    └── PROCEDURE_OCCURRENCE.parquet
```

Extraction will start automatically after populating the queues.  If granular
customisation of the rate per queue is required or a queue should not be started
then supply the argument `--no-start` and use `pixl start...` to launch
processing.

Once the messages have been processed, the OMOP extracts (including radiology reports) can be
exported to a `parquet file` using

```sh
pixl export-patient-data </path/to/parquet_dir>
```

Stop Imaging extraction

```bash
pixl stop
```

## Development

The CLI is created using [click](https://click.palletsprojects.com/en/8.0.x/), and curently provides
the following commands:

```sh
$ pixl --help
Usage: pixl [OPTIONS] COMMAND [ARGS]...

  PIXL command line interface

Options:
  --debug / --no-debug
  --help                Show this message and exit.

Commands:
  extract-radiology-reports  Export processed radiology reports to...
  kill                       Stop all the PIXL services
  populate                   Populate a (set of) queue(s) from a parquet...
  start                      Start consumers for a set of queues
  status                     Get the status of the PIXL consumers
  stop                       Stop extracting data
  update                     Update one or a list of consumers with a...
```

Install locally in editable mode with the development and testing dependencies by running

```bash
python -m pip install -e ../pixl_core/ -e ".[test]"
```

### Running tests

The CLI tests require a running instance of the `rabbitmq` service, for which we provide a
`docker-compose` [file](./tests/docker-compose.yml). The service is automatically started by the
`run_containers` _pytest_ fixture. So to run the tests, run

```bash
pytest
```
