# PIXL System Tests

This directory contains a system/integration test that runs locally and aims to test the essential
functionality of the full PIXL system.

**Given** a DICOM image in an Orthanc instance (mocked vendor neutral archive, VNA) and a single
patient with the same identifier in a postgres instance (mocked EMAP database, star schema).

**When** a message containing the patient and study identifier is added to the queue and the
consumers started.

**Then** a row in the "anon" EMAP data instance of the PIXL postgres instance exists and the DICOM
study exists in the "anon" PIXL Orthanc instance.

You can run the system test with:

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

Run the following to teardown:
```bash
./run-system-test.sh teardown
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

#### FTP server

We spin up a test FTP server from the Docker container defined in `./dummy-services/ftp-server/`.
The Docker container inherits from
[`delfer/alpine-ftp-server`](https://github.com/delfer/docker-alpine-ftp-server) and uses `vsftpd`
as the FTP client. The Docker container requires the following environment variables to be defined:

-   `ADDRESS`: external address to which clients can connect for passive ports
-   `USERS`: space and `|` separated list of usernames, passwords, home directories and groups:
    -   format `name1|password1|[folder1][|uid1][|gid1] name2|password2|[folder2][|uid2][|gid2]`
    -   the values in `[]` are optional
-   `TLS_KEY`: keyfile for the TLS certificate
-   `TLS_CERT`: TLS certificate

> [!warning] The `ADDRESS` should match the `FTP_HOST` environment variable defined in `.env`,
> otherwise FTP commands such as `STOR` or `dir` run from other Docker containers in the network
> (such as `orthanc-anon`) will fail. _Note: connecting and logging into the FTP server might still
> work, as the address name is only checked for protected operations such as listing and transfering
> files._

**Volume**: to check succesful uploads, we mount a local data directory to `/home/${FTP_USERNAME}/`

**SSL certifcates**: the SSL certificate files are defined in `test/dummy-services/ftp-server/ssl`
and are copied into `/etc/ssl/private` when building the Docker container.

### Resources

-   `./resources/` provides 2 mock DICOM images used to populate the mock VNA
    and a JSON file of slice varying parameters from a 3D MRI sequence.
-   `./resources/omop` contains mock public and private Parquet files used to populate the message
    queues and extract the radiology reports

### VNA config

`./vna-config` contains the Orthanc configuration files for the mock VNA.
