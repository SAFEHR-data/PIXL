# PIXL Imaging API

The PIXL imaging API processes messages created by the [CLI](../cli/README.md) and sent to imaging queues
to query images from a dicom server and transfer them to the [`orthanc-raw` instance](../orthanc/orthanc-raw/README.md).

The imaging API has two queues:

- `imaging-primary`, for querying the VNA
- `imaging-secondary`, for querying PACS

The imaging API uses RabbitMQ to expose a single HTTP endpoint that expects a JSON-formatted message structured as
defined by the [`Message`](../pixl_core/src/core/patient_queue/message.py) class in `pixl_core/patient_queue`.

Users should send messages to the `imaging-primary` queue only. On arrival of the input message, the imaging API
will query the VNA for the requested study. If the study does not exist in the VNA, the input message will be sent
to the `imaging-secondary` queue for processing. When the `imaging-secondary` queue processes a message, if the
study does not exist in PACS an error is raised.

If the study has be identified in VNA or PACS, a query to `orthanc-raw` is made to check if the study already
exists locally. If it does exist locally, a check is made to ensure all instances exist locally and any missing
instances are retrieved. If the study does not exist locally, the entire study is retrieved from the archive.

Once the study and all its instances are in `orthanc-raw`, the study is sent to `orthanc-anon` via a C-STORE
operation.

>[!NOTE]  
> When querying the archives, if we do not know the `StudyInstanceUID` we will query by MRN and Accession Number.
> This may result in multiple studies being found in the archives. In this instance, all studies returned by the
> query will be retrieved and sent to Orthanc Anon for anonymisation. In Orthanc Anon, the studies will be combined
> into a single study as they share the same MRN and Accession Number.

## Installation

```bash
python -m pip install --upgrade pip
python -m pip install -e pytest-pixl/
python -m pip install -e "pixl_core/[test]"
python -m pip install -e "pixl_imaging/[test]"
```

## Test


```bash
cd pixl_imaging/tests
pytest
```

## Usage

Usage should be from the CLI driver, which interacts with the endpoint.


## Configuration and database interaction

The database tables are updated using alembic, see the [alembic](alembic) dir for more details.

The `SKIP_ALEMBIC` environmental variable is used to control whether migrations are applied to the database (see variable at '.env.sample' and 'test/.env').

- `SKIP_ALEMBIC` is set to true for tests that do not use the database (e.g. `SKIP_ALEMBIC=true`). Otherwise you probably want to run this.
- If you wanted to test out new migrations from a test/dev deployment on the GAE with data in,
  then you can redeploy just the `imaging-api` container while keeping the `postgres` container up. 

## 'PIXL/pixl_imaging' Directory Contents

### Subdirectories

[alembic](./alembic/README.md)

[scripts](./scripts/README.md)

[src](./src/README.md)

[tests](./tests/README.md)

### Files

pyproject.toml

README.md

