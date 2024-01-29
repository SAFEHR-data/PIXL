# PIXL Driver + Command line interface

The PIXL CLI driver provides functionality to populate a queue with messages
containing information required to run electronic health queries against the
EMAP star database and the PACS image system. Once a set of queues are
populated the consumers can be started, updated and the system extractions
stopped cleanly.

## Development

### Prerequisites

`PIXL CLI` requires Python version 3.10 or higher.

The CLI requires a `pixl_config.yml` file in the current working directory. A [sample
file](../pixl_config.yml.sample) is provided in the root of the repository. For local testing, we
recommend running `pixl` from the [`./tests/`](./tests/) directory, which contains a mock
`pixl_config.yml` file.

Running the tests requires [docker](https://docs.docker.com/get-docker/) to be installed.

### Installation

We recommend installing in a project specific virtual environment created using a environment
management tool such as [conda](https://docs.conda.io/en/latest/) or [virtualenv](https://virtualenv.pypa.io/en/latest/).

Then install in editable mode by running

```bash
pip install -e ../pixl_core/ .
```

### Running tests

The CLI tests require a running instance of the `rabbitmq` service, for which we provide a
`docker-compose` [file](./tests/docker-compose.yml). Spinning up the service and running `pytest`
can be done by running

```bash
./tests/run-tests.sh
```

## Usage

> **Note**
> The `rabbitmq` service must be started prior to using the CLI

See the commands and subcommands with

```bash
pixl --help
```

Populate queue for PACS and EHR extraction

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

Start the imaging extraction

```bash
pixl start --queues pacs
```

and equivalently the EHR extraction

```bash
pixl start --queues ehr
```

Use `pixl start --help` for information.

Stop PACS and EHR database extraction

```bash
pixl stop
```
