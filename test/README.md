# PIXL System Tests

This directory contains a system/integration test that runs locally and aims to test the essential
functionality of the full PIXL system.

**Given** a DICOM image in an Orthanc instance (mocked vendor neutral archive, VNA) and a single
patient with the same identifier in a postgres instance (mocked EMAP database, star schema).

**When** a message containing the patient and study identifier is added to the queue and the
consumers started.

**Then** a row in the "anon" EMAP data instance of the PIXL postgres instance exists and the DICOM
study exists in the "anon" PIXL Orthanc instance.

After setting up your [.secrets.env](../README.md#project-secrets)), you can run the system test with:

```bash
./run-system-test.sh
```

Or to do all the setup but not run any tests:
```bash
./run-system-test.sh setup
```

You can then develop and run tests repeatedly with `pytest` or through your IDE.
But you are responsible for knowing
when to re-run the setup if something it depends on has changed.
Currently, the postgres container doesn't get properly set/reset by the tests so you may have
to re-run setup if you want to re-run certain tests.

Run the following to teardown:
```bash
./run-system-test.sh teardown
```

## The `pytest-pixl` plugin

We provide a [`pytest` plugin](../pytest-pixl/README.md) with shared functionality for PIXL system
and unit tests. This includes an `ftp_server` fixture to spin up a lightweight FTP server,
to mock the FTP server used by the Data Safe Haven.

## File organisation

### Docker compose

`./docker-compose.yml` contains the docker compose configuration for the system test.

### Scripts

`./scripts` contains bash and Python scripts to check the individual components of the system test.

### Dummy services

`./dummy-services` contains a Python script and Dockerfile to mock the CogStack service, used for
de-identification of the radiology reports in the EHR API.

### Resources

-   `./resources/` provides 2 mock DICOM images used to populate the mock VNA
    and a JSON file of slice varying parameters from a 3D MRI sequence.
-   `./resources/omop` contains mock public and private Parquet files used to populate the message
    queues and extract the radiology reports

### VNA config

`./vna-config` contains the Orthanc configuration files for the mock VNA.
