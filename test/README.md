# PIXL System Tests

This directory contains a system/integration test that runs locally and aims to
test the essential functionality of the full PIXL system.

**Given** a DICOM image in an Orthanc instance (mocked vendor
neutral archive, VNA) and a single patient with the same identifier in a
postgres instance (mocked EMAP database, star schema).
**When** a message containing the patient and study identifier is added to the
queue and the consumers started.
**Then** a row in the "anon" EMAP data instance of the PIXL postgres instance exists
and the DICOM study exists in the "anon" PIXL Orthanc instance.

You can run the system test with:

```bash
./run-system-test.sh
```

## File organisation

### PIXL configuration

A test `pixl_config.yml` file is provided to run the PIXL pipeline.

### Docker compose

`./docker-compose.yml` contains the docker compose configuration for the system test.

### Scripts

`./scripts` contains bash and Python scripts to check the individual components of the system test.

### Dummy services

`./dummy-services` contains a Python script and Dockerfile to mock the CogStack service, used for
de-identification of the radiology reports in the EHR API.

### Resources

- `./resources/` provides 2 mock DICOM images used to populate the mock VNA.
- `./resources/omop` contains mock public and private Parquet files used to populate the message
  queues and extract the radiology reports

### VNA config

`./vna-config` contains the Orthanc configuration files for the mock VNA.
