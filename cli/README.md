# PIXL Driver + Command line interface


## Installation

```bash
cd src && pip install -r requirements.txt . 
```

<details>
    <summary>Deploying apache-manager locally on an ARM Mac</summary>

    The apache-manager v0.3.0 docker container is broken, thus the dashboard UI must be 
    deployed from the [tar-ed binary](https://github.com/apache/pulsar-manager#deploy-from-bin-package).
    Once up, access the UI at `http://localhost:7750/ui/index.html`
</details>


## Usage

> **Note**
> Services must be started prior to using the CLI

Populate queue for PACS and EHR extraction
```bash
pixl populate <filename>.csv
```
where the csv file contains MRN, accession numbers and timestamps.

Start the PACS extraction
```bash
pixl start pacs
```
and equivalently the EHR extraction
```bash
pixl start ehr
```

both of the start commands take optional flags. Use `pixl start ehr --help` for 
information.

Stop PACS and EHR database extraction
```bash
pixl stop
```
