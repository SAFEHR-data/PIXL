# PIXL System Tests

This directory contains a system/integration test that runs locally and aims to test the essential
functionality of the full PIXL system.

**Given** a DICOM image in an Orthanc instance (mocked vendor neutral archive, VNA)

**When** a message containing the patient and study identifier is added to the queue and the
consumers started.

**Then** the DICOM study exists in the "anon" PIXL Orthanc instance.

## Pre-requisites for running system tests

Set up your [.secrets.env](/README.md#project-secrets)

Make sure your [python virtual environment](/docs/setup/developer.md) has been set up, PIXL installed correctly,
and the virtual environment activated.

## Running system tests

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

## Viewing telemetry

### Default: the bundled LGTM stack

By default the system tests are self-contained: the `lgtm` service (an all-in-one
[Grafana LGTM](https://github.com/grafana/docker-otel-lgtm) stack) in
[`docker-compose.yml`](./docker-compose.yml) is the observability backend, and it
comes up automatically with `./run-system-test.sh`. PIXL services export to it as
`http://lgtm:4317` (see [`test/.env`](./.env)), and it scrapes the RabbitMQ queue
metrics via [`prometheus.yaml`](./prometheus.yaml).

While the containers are up, open the Grafana UI at
[http://localhost:3001](http://localhost:3001) and log in with the credentials set
for the `lgtm` service in [`docker-compose.yml`](./docker-compose.yml).

### Using the external telemetry stack instead

Instead of the bundled LGTM you can export to the shared telemetry stack in the
[`telemetry`](https://github.com/SAFEHR-data/telemetry) repo (PIXL → otel-agent →
gateway → Grafana). Set that stack up first — see its `README.md` ("Running") and
`sandbox/README.md` (`make -C sandbox up`) — then:

1. Bring PIXL up (`./run-system-test.sh setup`) so this compose project's network
   `system-test_pixl-net` exists.
2. Start the telemetry otel-agent joined to that network via its host override. In
   the `telemetry` repo's `otel-agent/` directory, set
   `PIXL_NETWORK=system-test_pixl-net` and run:
   ```bash
   docker compose -f docker-compose.yml -f host_overrides/compose.gae14.override.yml up -d
   ```
   Compose exposes the agent on that network as `otel-agent`.
3. Point PIXL at it: set `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-agent:4317` —
   edit [`test/.env`](./.env), or `export` it before running
4. RabbitMQ metrics are then scraped by the agent's
   `config/apps/rabbitmq-scrape.yaml` fragment rather than the bundled
   `prometheus.yaml`. The bundled `lgtm` can be left running (the offset ports don't
   clash) but is redundant on this path, or you can comment it out.

Inspect the resulting telemetry in the telemetry stack's Grafana.

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
