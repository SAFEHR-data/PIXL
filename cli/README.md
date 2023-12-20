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
pixl populate <filename>.csv
```

where the csv file contains MRN, accession numbers and timestamps in the format:

| VAL_ID | ACCESSION_NUMBER | STUDY_INSTANCE_UID | STUDY_DATE       | ... |
|--------|------------------|--------------------|------------------|-----|
| X      | Y                | Z                  | 29/02/2010 05:12 |     |

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
