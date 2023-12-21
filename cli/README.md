# PIXL Driver + Command line interface

The PIXL CLI driver provides functionality to populate a queue with messages
containing information required to run electronic health queries against the
EMAP star database and the PACS image system. Once a set of queues are
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

Populate queue for PACS and EHR extraction

```bash
pixl populate --parquet-dir </path/to/parquet_dir>
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

Start the PACS extraction

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
