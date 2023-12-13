# PIXL

PIXL Image eXtraction Laboratory

`PIXL` is a system for extracting, linking and de-identifying DICOM imaging data, structured EHR data and free-text data from radiology reports at UCLH.
Please see the [wiki](https://github.com/UCLH-Foundry/PIXL/wiki) for more details.

PIXL is intended run on one of the [GAE](https://github.com/UCLH-Foundry/Book-of-FlowEHR/blob/main/glossary.md#gaes)s and comprises
several services orchestrated by [Docker Compose](https://docs.docker.com/compose/).

## Services

### [PIXL CLI](./cli/README.md)

Primary interface to the PIXL system.

### [Hasher API](./hasher/README.md)

HTTP API to securely hash an identifier using a key stored in Azure Key Vault.

### [Orthanc Raw](./orthanc/orthanc-raw/README.md)

A DICOM node which receives images from the upstream hospital systems and acts as cache for PIXL.

### [Orthanc Anon](./orthanc/orthanc-anon/README.md)

A DICOM node which wraps our de-identifcation and cloud transfer components.

### PostgreSQL

RDBMS which stores DICOM metadata, application data and anonymised patient record data.

### [Electronic Health Record Extractor](./pixl_ehr/README.md)

HTTP API to process messages from the `ehr` queue and populate raw and anon tables in the PIXL postgres instance.

### [PACS Image Extractor](./pixl_pacs/README.md)

HTTP API to process messages from the `pacs` queue and populate the raw orthanc instance with images from PACS/VNA.

## Setup

### 0. Choose deployment environment

This is one of dev|test|staging|prod and referred to as `<environment>` in the docs.

### 1. Initialise environment configuration

Create a local `.env` and `pixl_config.yml` file in the _PIXL_ directory:

```bash
cp .env.sample .env && cp pixl_config.yml.sample  pixl_config.yml
```

Add the missing configuration values to the new files:

#### Environment

Set `ENV` to `<environment>`.

#### Credentials

- `EMAP_DB_`*  
UDS credentials are only required for `prod` or `staging` deployments of when working on the EHR & report retriever component.  
You can leave them blank for other dev work.
- `PIXL_DB_`*  
These are credentials for the containerised PostgreSQL service and are set in the official PostgreSQL image.
Use a strong password for `prod` deployment but the only requirement for other environments is consistency as several services interact with the database.
- `PIXL_EHR_API_AZ_`*
These credentials are used for uploading a PIXL database to Azure blob storage. They should be for a service principal that has `Storage Blob Data Contributor`
on the target storage account. The storage account must also allow network access from the PIXL host machine.

#### Ports

Most services need to expose ports that must be mapped to ports on the host. The host port is specified in `.env`  
Ports need to be configured such that they don't clash with any other application running on that GAE.  

#### Storage size

The maximum storage size of the `orthanc-raw` instance can be configured through the `ORTHANC_RAW_MAXIMUM_STORAGE_SIZE`
environment variable in `.env`. This limits the storage size to the specified value (in MB). When the storage is full
[Orthanc will automatically recycle older studies in favour of new ones](https://orthanc.uclouvain.be/book/faq/features.html#id8).

## Run

### Start

From the _PIXL_ directory:

```bash
bin/pixldc pixl_dev up
```

### Stop

From the _PIXL_ directory:

```bash
bin/pixldc pixl_dev down
```

## Analysis

The number of DICOM instances in the raw Orthanc instance can be accessed from
`http://<pixl_host>:<ORTHANC_RAW_WEB_PORT>/ui/app/#/settings` and similarly with
the Orthanc Anon instance, where `pixl_host` is the host of the PIXL services
and `ORTHANC_RAW_WEB_PORT` is defined in `.env`.

The number of reports and EHR can be interrogated by connecting to the PIXL
database with a database client (e.g. [DBeaver](https://dbeaver.io/)), using
the connection parameters defined in `.env`. For example, to find the number of
non-null reports

```sql
select count(*) from emap_data.ehr_anon where xray_report is not null;
```

## Develop

See each service's README for instructions for individual developing and testing instructions.
For Python development we use [isort](https://github.com/PyCQA/isort) and [black](https://black.readthedocs.io/en/stable/index.html) alongside [pytest](https://www.pytest.org/).
There is support (sometimes through plugins) for these tools in most IDEs & editors.  
Before raising a PR, **run the full test suite** from the _PIXL_ directory with

```bash
bin/run-all-tests.sh
```

and not just the component you have been working on as this will help us catch unintentional regressions without spending GH actions minutes :-)

We run [pre-commit](https://pre-commit.com/) as part of the GitHub Actions CI. To install and run it locally, do:

```sh
pip install pre-commit
pre-commit install
```

The configuration can be found in [`.pre-commit-config.yml`](./.pre-commit-config.yaml)

## Assumptions

PIXL data extracts include the below assumptions

- (MRN, Accession number) is unique identifier for a report/DICOM study pair
- Patients have a single _relevant_ MRN
