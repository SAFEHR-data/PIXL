# PIXL Driver + Command line interface

The PIXL CLI driver provides functionality to populate a queue with messages containing information
required to run electronic health queries against the VNA image system.
Once a set of queues are populated the consumers can be started, updated and the system extractions
stopped cleanly.

## Prerequisites
* Python version 3.11 (matching python versions in [pixl-ci](../.github/workflows/main.yml) and [dev](../docs/setup/developer.md#installation-of-pixl-modules)).
* [Docker](https://docs.docker.com/get-docker/) with version `>=27.0.3`
* [Docker Compose](https://docs.docker.com/compose/install/#installation-scenarios) with version `>=v2.28.1-desktop.1`
* We recommend installing PIXL project in specific virtual environment using a environment
management tool such as [conda](https://docs.conda.io/en/latest/) or
[virtualenv](https://virtualenv.pypa.io/en/latest/). 
See detailed instructions [here](../docs/setup/developer.md#setting-up-python-virtual-environment)

## Installation
Activate your python virtual environment and install `PIXL` project in editable mode by running
```bash
python -m pip install -e ../pixl_core -e .
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

Populate queue for Imaging using parquet files:

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

Alternatively, the queue can be populated based on records in CSV files:

```bash
pixl populate <path/to/file.csv>
```

One advantage of using a CSV file is that multiple projects can be listed
for export in the file. Using the parquet format, in contrast, only supports
exporting a single project per call to `pixl populate`.

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

### High-priority messages

By default, messages will be sent to the queue with the lowest priority (1).

To send to the queue with a different priority, you can use the `--priority` argument to
`populate`:

```bash
pixl populate --priority 5 <path/to/file.csv>
```

`priority` must be an integer between 1 and 5, with 5 being the highest priority.

## Development
### Help commands
The CLI is created using [click](https://click.palletsprojects.com/en/8.0.x/). To see which commands
are currently available, you can use the `pixl --help` command:

### Local installation
Activate your python environment and install project locally in editable mode with the development and testing dependencies by running
```bash
python -m pip install -e ../pixl_core -e ../pytest-pixl -e ".[test]" -e ".[dev]"
```

### Running tests
The CLI tests require a running instance of the `rabbitmq` service, for which we provide a
`docker-compose` [file](./tests/docker-compose.yml). The service is automatically started by the
`run_containers` _pytest_ fixture. So to run the tests, run

```bash
pytest -vs tests #for all tests
pytest -vs tests/test_docker_commands.py #e.g., for particular tests
```
