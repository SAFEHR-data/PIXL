# Core

This module contains the core PIXL functionality utilised by both the EHR and Imaging APIs to
interact with the RabbitMQ messaging queues and ensure suitable rate limiting of requests to the
upstream services.

Specifically, it defines:

- The [Token buffer](#token-buffer) for rate limiting requests to the upstream services
- The [RabbitMQ queue](#patient-queue) implementation shared by the EHR and Imaging APIs
- The PIXL `postgres` internal database for storing exported images and extracts from the messages
  processed by the CLI driver
- The [`ParquetExport`](./src/core/exports.py) class for exporting OMOP and EMAP extracts to parquet files
- Handling of [uploads over FTPS](./src/core/upload.py), used to transfer images and parquet files
  to the DSH (Data Safe Haven)

## Installation

```bash
pip install -e .
```

## Testing

```bash
pip install -e .[test]
pytest
```

## Token buffer

The token buffer is needed to limit the download rate for images from PAX/VNA. Current specification
suggests that a rate limit of five images per second should be sufficient, however that may have to
be altered dynamically through command line interaction.

The current implementation of the token buffer uses the [token bucket implementation from
Falconry](https://github.com/falconry/token-bucket/). Furthermore, the token buffer is not set up as
a service as it is only needed for the image download rate.

## Patient queue

We use [RabbitMQ](https://www.rabbitmq.com/) as a message broker to transfer messages between the
different PIXL services. Currently, we define two queues:

1. `pacs` for downloading and de-identifying images
2. `ehr` for downloading and de-identifying the EHR data

The image anonymisation will be triggered automatically once the image has been downloaded to the raw Orthanc server.

### RabbitMQ

RabbitMQ is used for the queue implementation.

The client of choice for RabbitMQ at this point in time is
[pika](https://pika.readthedocs.io/en/stable/), which provides both a synchronous and asynchronous
way of transferring messages. The former is geared towards high data throughput whereas the latter
is geared towards stability.  The asynchronous mode of transferring messages is a lot more complex
as it is based on the [asyncio event loop](https://docs.python.org/3/library/asyncio-eventloop.html).

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

## Uploading to an FTPS server

The `core.upload` module implements functionality to upload DICOM tags and parquet files to an
**FTPS server**. This requires the following environment variables to be set:

-   `FTP_HOST`: URL to the FTPS server
-   `FTP_PORT`: port on which the FTPS server is listening
-   `FTP_USER_NAME`: name of user with access to the FTPS server
-   `FTP_USER_PASSWORD`: password for the authorised user

We provide mock values for these for the unit tests (see
[`./tests/conftest.py`](./tests/conftest.py)). When running in production, these should be defined
in the `.env` file (see [the example](../.env.sample)).
