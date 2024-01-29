# PIXL Driver + Command line interface

The PIXL CLI driver provides functionality to populate a queue with messages
containing information required to run electronic health queries against the
EMAP star database and the VNA image system. Once a set of queues are
populated the consumers can be started, updated and the system extractions
stopped cleanly.

## Installation

```bash
pip install -e ../pixl_core/ .
```

## Test

```bash
./tests/run-tests.sh
```

## Usage

> **Note**
> Services must be started prior to using the CLI

See the commands and subcommands with

```bash
pixl --help
```

Populate queue for Imaging and EHR extraction

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

Start the Imaging extraction

```bash
pixl start --queues imaging
```

and equivalently the EHR extraction

```bash
pixl start --queues ehr
```

Use `pixl start --help` for information.

Stop Imaging and EHR database extraction

```bash
pixl stop
```
