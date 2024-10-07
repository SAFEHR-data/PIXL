# PIXL System Tests

This directory contains a system/integration test that runs locally and aims to test the essential
functionality of the full PIXL system.

**Given** a DICOM image in an Orthanc instance (mocked vendor neutral archive, VNA)

**When** a message containing the patient and study identifier is added to the queue and the
consumers started.

**Then** the DICOM study exists in the "anon" PIXL Orthanc instance.

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

For CI, there is also another subcommand to run pytest, reporting coverage
```bash
./run-system-test.sh coverage
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

### Resources

-   `./resources/` provides 2 mock DICOM images used to populate the mock VNA
    and a JSON file of slice varying parameters from a 3D MRI sequence.
-   `./resources/omop` contains mock public and private Parquet files used to populate the message
    queues and extract the radiology reports
-  `./resources/omop-dicomweb` contains the same mock public and private Parquet files as above
but configured to upload to a [DICOMweb server](#dicomweb-config)

### VNA config

`./vna-config` contains the Orthanc configuration files for the mock VNA.

### DICOMWeb config

`./dicomweb_config/` contains the Orthanc configuration files for the mock [DICOMweb server](../docs/services/dicomweb-server.md).
