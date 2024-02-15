# PIXL Imaging API

The PIXL imaging API processes messages from the imaging queue created by the [CLI](../cli/README.md) 
to query images from the [VNA](https://en.wikipedia.org/wiki/Vendor_Neutral_Archive) and transfers them to the [`orthanc-raw` instance](../orthanc/orthanc-raw/README.md).
It is identical in structure the [EHR API](../pixl_ehr/README.md).

It exposes a single HTTP endpoint that expects a JSON-formatted message structured as defined by the
[`Message`](../pixl_core/src/core/patient_queue/message.py) class in `pixl_core/patient_queue`.
On arrival of the input message it will issue a DICOMWeb request to `orthanc-raw`, which then queries the VNA
for the requested imaging study, if it didn't already exist.

## Installation

```bash
pip install -e ../pixl_core/ .
```

## Test

```bash
./tests/run-tests.sh
```

## Usage

Usage should be from the CLI driver, which interacts with the endpoint.


## Configuration and database interaction

The database tables are updated using alembic, see the [alembic](alembic) dir for more details.

The `SKIP_ALEMBIC` environmental variable is used to control whether migrations are applied to the database.

- Tests that don't use the database use `SKIP_ALEMBIC=true`, but otherwise you probably want to run this.
- If you wanted to test out new migrations from a test/dev deployment on the GAE you may want to set
skip alembic migrations
  - Editing the `.env` file to skip alembic 
  - Re-recreate the `pixl-imaging` container keeping the existing postgres container up 
  - Connect to the container and try applying the new migration(s) manually by running
  ```shell
  cd /app/alembic
  alembic upgrade head
  ```
