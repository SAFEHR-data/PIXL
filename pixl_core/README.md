# Core

This module contains the core PIXL functionality utilised by both the Imaging API to
interact with the RabbitMQ messaging queues and ensure suitable rate limiting of requests to the
upstream services.

Specifically, it defines:

- The [Token buffer](#token-buffer) for rate limiting requests to the upstream services
- The [RabbitMQ queue](#patient-queue) implementation shared by the Imaging API and any other APIs
- The PIXL `postgres` internal database for storing exported images and extracts from the messages
  processed by the CLI driver
- The [`ParquetExport`](./src/core/exports.py) class for exporting OMOP extracts to
  parquet files
- Pydantic models for [project configuration](./src/core/project_config/pixl_config_model.py)
- [Secrets management](./src/core/project_config/secrets.py) via an Azure Key Vault.
- Handling of [uploads over FTPS](./src/core/uploader/_ftps.py), used to transfer images and parquet files
  to the DSH (Data Safe Haven)
- [Uploading DICOM files to a DICOMWeb server](./src/core/uploader/_dicomweb.py)
- [Uploading DICOM files to XNAT](./src/core/uploader/_xnat.py)

## Installation

```bash
uv sync
```

## Testing

```bash
pytest
```

## Token buffer

The token buffer is needed to limit the download rate for images from PAX/VNA. Current specification
suggests that a rate limit of five images per second should be sufficient, however that may have to
be altered dynamically through command line interaction.

The current implementation of the token buffer uses the
[token bucket implementation from Falconry](https://github.com/falconry/token-bucket/). Furthermore,
the token buffer is not set up as a service as it is only needed for the image download rate.

## Patient queue

We use [RabbitMQ](https://www.rabbitmq.com/) as a message broker to transfer messages between the
different PIXL services. Currently, we define one queue:

1. `imaging` for downloading and de-identifying images

The image anonymisation will be triggered automatically once the image has been downloaded to the
raw Orthanc server.

### RabbitMQ

RabbitMQ is used for the queue implementation.

The client of choice for RabbitMQ at this point in time is
[pika](https://pika.readthedocs.io/en/stable/), which provides both a synchronous and asynchronous
way of transferring messages. The former is geared towards high data throughput whereas the latter
is geared towards stability. The asynchronous mode of transferring messages is a lot more complex as
it is based on the [asyncio event loop](https://docs.python.org/3/library/asyncio-eventloop.html).

We set the maximum number of message which can be being processed at once using the `PIXL_MAX_MESSAGES_IN_FLIGHT`
variable in the `.env` file. The VNA allows for 5 DICOM transfers at a single point in time, so the default is 5.
We recommend allowing more concurrent jobs using `ORTHANC_CONCURRENT_JOBS`, to allow for resource modification
and export of stable DICOM to orthanc-anon while still pulling from the VNA.

### OMOP ES files

Public parquet exports from OMOP ES that should be transferred outside the hospital are copied to
the `exports` directory at the repository base.

Within this directory each project has a directory, with all extracts stored in `all_extracts` and
for convenience `latest` is a symlink to the most recent extract.

```sh
└── project-1
    ├── all_extracts
    │     ├── 2020-06-10t18-00-00
    │     │   ├── radiology
    │     │   └── omop
    │     │       └── public
    │     └── 2020-07-10t18-00-00
    │         ├── radiology
    │         └── omop
    │             └── public
    └── latest -> all_extracts/2020-07-10t18-00-00
└── project-2
    ├── all_extracts
    │     └── 2023-12-13t16-22-40
    │         ├── radiology
    │         └── omop
    │             └── public
    └── latest -> all_extracts/2023-12-13t16-22-40
```

## Project configuration

The `project_config` module provides the functionality to handle
[project configurations](../README.md#configure-a-new-project).

### Design

![](../docs/design/diagrams/pixl-multi-project-config.png)

## Uploading to an FTPS server

The `core.uploader` module implements functionality to upload DICOM images and parquet files to
several destinations.

The `Uploader` abstract class provides a consistent interface for uploading files. Child classes
such as the `FTPSUploader` implement the actual upload functionality. The credentials required for
uploading are queried from an **Azure Keyvault** instance (implemented in `core.project_config.secrets`), for which
the setup instructions are in the [top-level README](../README.md#project-secrets)

When an extract is ready to be published to the DSH, the PIXL pipeline will upload the **Public**
and **Radiology** [_parquet_ files](../docs/file_types/parquet_files.md) to the `<project-slug>` directory
where the DICOM datasets are stored (see the directory structure below). The uploading is controlled
by `upload_parquet_files` in [`upload.py`](./src/core/upload.py) which takes a `ParquetExport`
object as input to define where the _parquet_ files are located.  `upload_parquet_files` is called
by the `export-patient-data` API endpoint defined in the
[Export API](../pixl_export/src/pixl_export/main.py), which in turn is called by the `export_patient_data`
command in the [PIXL CLI](../cli/README.md).

Once the parquet files have been uploaded to the DSH, the directory structure will look like this:

```sh
<project-slug>
    ├── <extract_datetime_slug>
    │   └── parquet
    │       ├── omop
    │       │   └── public
    │       │       └── PROCEDURE_OCCURRENCE.parquet
    │       └── radiology
    │           └── radiology.parquet
    ├── <pseudonymised_ID_DICOM_dataset_1>.zip
    └── <pseudonymised_ID_DICOM_dataset_2>.zip
```

## Uploading to a DICOMweb server

PIXL supports [DICOMweb](../docs/services/dicomweb-server.md) as an alternative upload destination
for the DICOM images for a given project.

The `DicomwebUploader` class in the `core.uploader` module handles the communication between the
Orthanc server where anonymised DICOM images are stored and the DICOMweb server where the images
should be sent to. We make use of the [Orthanc DICOMweb plugin](https://orthanc.uclouvain.be/book/plugins/dicomweb.html)
to implement this.

### Configuration

The configuration for the DICOMweb server is controlled by the following environment variables and secrets:

- `"ORTHANC_ANON_URL"`: The URL of the Orthanc server from _where_ the upload will happen, this will typically be the `orthanc-anon` instance
- The `"<project_slug>--dicomweb--username"` and `"<project_slug>--dicomweb--password"` for authentication, which are fetched from the [Azure Keyvault](../docs/setup/azure-keyvault.md)
- The `"<project_slug>--dicomweb--url"` to define the DICOMweb endpoint in Orthanc, also fetched from the Azure Keyvault

We dynamically configure the DICOMweb server endpoint in Orthanc (see `core.uploader._dicomweb.DicomWebUploader._setup_dicomweb_credentials()`),
so we can have different (or no) endpoints for different projects.

### Testing setup

For [testing](../test/README.md) we set up an additional Orthanc server that acts as a DICOMweb server,
using the vanilla Orthanc Docker image with the DICOMWeb plugin enabled.

## Uploading to an XNAT instance

PIXL also supports sending DICOM images to an [XNAT](https://www.xnat.org/) instance.

The `XNATUploader` class in `core.uploader._xnat` handles downloading anonymised images from Orthanc and
sending to XNAT. [XNATPy](https://xnat.readthedocs.io/en/latest/) is used to upload the
data to XNAT using the
[`DICOM-zip` Import Handler](https://wiki.xnat.org/xnat-api/image-session-import-service-api#ImageSessionImportServiceAPI-SelectAnImportHandler).

To use XNAT as an endpoint, first:

- a user will need to be created on the XNAT instance to perform the upload with PIXL
- a project will need to be created on the XNAT instance. It is assumed the user created for uploading
  data does not have admin permissions to create new projects

### XNAT endpoint Configuration

Configuration for XNAT as an endpoint is done by storing the following secrets in an Azure Key Vault:

```bash
"${az_prefix}--xnat--host"  # hostname for the XNAT instance
"${az_prefix}--xnat--username"  # username of user to perform upload
"${az_prefix}--xnat--password"  # password of user to perform upload
"${az_prefix}--xnat--port"  # port for connecting to the XNAT instance
```

where `az_prefix` is either the project slug or is defined in the [project configuration file](../template_config.yaml)
as `azure_kv_alias`.

> Note
>
> The project name defined in the configuration file **must** match the
> [XNAT Project ID](https://wiki.xnat.org/documentation/creating-and-managing-projects). If the project name does
> not match the XNAT Project ID, the upload will fail.

The following environment variables must also be set to determine the XNAT destination and how to handle conflicts
with existing session and series data:

`"XNAT_DESTINATION"`:

- if `"/archive"`, will send data straight to the archive
- if `"/prearchive"`, will send data to the [prearchive](https://wiki.xnat.org/documentation/using-the-prearchive)
  for manual review before archiving

`"XNAT_OVERWRITE"`:

- if `"none"`, will error if the session already exists. Upon error, data will be sent to the prearchive,
  even if `XNAT_DESTINATION` is `/archive`
- if `"append"`, will append the data to an existing session or create a new one if it doesn't exist.
        If there is a conflict with existing series, an error will be raised.
- if `"delete"`, will append the data to an existing session or create a new one if it doesn't exist.
        If there is a conflict with existing series, the existing series will be overwritten.

### XNAT testing setup

For unit testing, we use [`xnat4tests`](https://github.com/Australian-Imaging-Service/xnat4tests) to spin up an XNAT
instance in a Docker container.

Secrets are not used for these unit testing. Instead, the following environment variables are used to configure XNAT for testing:

- `"XNAT_HOST"`
- `"XNAT_USER_NAME"`
- `"XNAT_PASSWORD"`
- `"XNAT_PORT"`

Note, it can take several minutes for the server to start up.

Once the server has started, you can log in by visiting `http://localhost:8080` with the username and password set
in the `XNAT_USER_NAME` and `XNAT_PASSWORD` environment variables.
