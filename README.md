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

### 0. UCLH infrastructure setup

<details>
<summary>Install shared miniforge installation if it doesn't exist</summary>

Follow the suggestion for installing a central [miniforge](https://github.com/conda-forge/miniforge)
installation to allow all users to be able to run modern python without having admin permissions.

```shell
# Create directory with correct structure
mkdir /gae/miniforge3
chgrp -R docker /gae/miniforge3
chmod -R g+rwxs /gae/miniforge3  # inherit group when new directories or files are created
setfacl -R -m d:g::rwX /gae/miniforge3
# Install miniforge
wget "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh -p /gae/miniforge3
conda update -n base -c conda-forge conda
conda create -n pixl_dev python=3.10.*
```

The directory should now have these permissions

```shell
> ls -lah /gae/miniforge3/
total 88K
drwxrws---+  19 jstein01 docker 4.0K Nov 28 12:27 .
drwxrwx---.  18 root     docker 4.0K Dec  1 19:35 ..
drwxrws---+   2 jstein01 docker 8.0K Nov 28 12:27 bin
drwxrws---+   2 jstein01 docker   30 Nov 28 11:49 compiler_compat
drwxrws---+   2 jstein01 docker   32 Nov 28 11:49 condabin
drwxrws---+   2 jstein01 docker 8.0K Nov 28 12:27 conda-meta
-rw-rws---.   1 jstein01 docker   24 Nov 28 11:49 .condarc
...
```

</details>
<details>

<summary>If you haven't just installed the miniforge yourself, update your configuration</summary>

Edit `~/.bash_profile` to add `/gae/miniforge3/bin` to the PATH. for example

```shell
PATH=$PATH:$HOME/.local/bin:$HOME/bin:/gae/miniforge3/bin
```

Run the updated profile (or reconnect to the GAE) so that conda is in your PATH

```shell
source ~/.bash_profile
```

Initialise conda

```shell
conda init bash
```

Run the updated profile (or reconnect to the GAE) so that conda is in your PATH

```shell
source ~/.bash_profile
```

Activate an existing pixl environment

```shell
conda activate pixl_dev
```

</details>
<details>
<summary>Create an instance for the GAE if it doesn't already exist</summary>

Select a place for the deployment. On UCLH infrastructure this will be in `/gae`, so `/gae/pixl_dev` for example.

```shell
mkdir /gae/pixl_dev
chgrp -R docker /gae/pixl_dev
chmod -R g+rwxs /gae/pixl_dev  # inherit group when new directories or files are created
setfacl -R -m d:g::rwX /gae/pixl_dev
# now clone the repository or copy an existing deployment
```

</details>

### 1. Choose deployment environment

This is one of dev|test|staging|prod and referred to as `<environment>` in the docs.

### 2. Initialise environment configuration

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
For Python development we use [ruff](https://docs.astral.sh/ruff/) alongside [pytest](https://www.pytest.org/).
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
