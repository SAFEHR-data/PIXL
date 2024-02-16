# FTPS server

Currently, we can only upload files to the Data Safe Haven (DSH) through an
[FTPS](https://en.wikipedia.org/wiki/FTPS) connection.

The [`core.upload`](../../pixl_core/src/core/upload.py) module implements functionality to upload
DICOM tags and parquet files to an **FTPS server**. This requires the following environment
variables to be set:

- `FTP_HOST`: URL to the FTPS server
- `FTP_PORT`: port on which the FTPS server is listening
- `FTP_USER_NAME`: name of user with access to the FTPS server
- `FTP_USER_PASSWORD`: password for the authorised user

We provide mock values for these for the unit tests (see
[`./tests/conftest.py`](./tests/conftest.py)). When running in production, these should be defined
in the `.env` file (see [the example](../.env.sample)).

For the `pixl_core` unit tests and the system test, we spin up an FTPS server with a Docker
container, defined in [`test/dummy-services/ftp-server`](../../test/dummy-services/ftp-server/) and
set the necessary environment variables in [`test/.env`](../../test/.env).

## FTPS test server

We provide a Docker container to spin up a test FTPS server. The documentation for this can be found
in [`test/README.md`](../../test/README.md).
