# PIXL Driver + Command line interface

## Usage

> **Note**
> The queue must exist prior to up-ing this service

Populate queue for PACS and image extraction
```bash
pixl up <filename>.csv
```
where the csv file contains MRN, accession numbers and timestamps.

Stop PACS and EHR database extraction
```bash
pixl stop
```

***

## Local installation

```bash
pip install -r requirements.txt .
```
