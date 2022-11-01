# PIXL Driver + Command line interface


## Installation

```bash
cd src && pip install -r requirements.txt . 
```

## Usage

> **Note**
> Services must be started prior to using the CLI

Populate queue for PACS and EHR extraction
```bash
pixl up <filename>.csv
```
where the csv file contains MRN, accession numbers and timestamps.

Stop PACS and EHR database extraction
```bash
pixl stop
```
