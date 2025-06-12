# Developer setup

## Setting up `Python` Virtual Environment (VE)

### Using `uv`
Once you have installed `uv`, in the root of your source tree you can:

Install the required Python version and create the venv (one-off task)
```
uv python install 3.11
uv venv --python 3.11
```
Enter the venv (for the lifetime of the shell)
```
source .venv/bin/activate
```

## Docker requirements 
Most modules require `docker` and `docker-compose` to be installed to run tests.
* [Docker](https://docs.docker.com/get-docker/) with version `>=27.0.3`
* [Docker Compose](https://docs.docker.com/compose/install/#installation-scenarios) with version `>=v2.28.1-desktop.1`

## Installation of `PIXL` modules

You can install all PIXL Python modules by running the following command from the `PIXL/` directory:

```shell
uv sync
```

See each service's README for instructions for individual developing and testing instructions.

### Non-editable installation

By default, `uv` will install `pixl` and its workspace members in editable mode. To install in non-editable mode:

```shell
uv sync --no-editable
```

You will need to set the `PIXL_ROOT`, `HOST_EXPORT_ROOT_DIR`, and `HOST_EXPORT_ROOT_DIR_MOUNT` environment
variables if you install PIXL in non-editable mode. See the [`cli` docs](../../cli/README.md#host-directories)
for more info.

## Testing

### Module-level testing

Once you have installed each module, you can run the tests for a module using the `pytest` command, e.g.

```shell
cd pixl_core/
pytest
```

Alternatively, you can run most of the module-level tests from the root of the repo with:

```shell
pytest #to test all tests `testpaths` pytest.ini
```

The `pytest.ini` file in the root of the repo contains the configuration for running most of the module-level tests at once.
However, `pixl_dcmd` and `hasher` have `conftests.py` files that clash, so only `pixl_dcmd` is included as a `testpath` in the
top-level `pytest.ini`. You will therefore need to run tests for `hasher` from the `hasher` directory.


#### Enabling default Docker socket for testing `pixl_core`

We have tests in `pixl_core` for uploading DICOM to XNAT as an endpoint. These tests use
[`xnat4tests`](https://github.com/Australian-Imaging-Service/xnat4tests) to spin up a docker container running XNAT.

`xnat4tests` requires you to allow the Docker daemon to listen for Docker Engine API requests via the default
socket. This is because `xnat4tests` set up the XNAT Container Service for launching other containers that run
analysis pipelines.

If you are using Docker Desktop, you will need to enable Docker to listen on the default socket by going to
`Settings > Advanced` and checking the box `Allow the default Docker socket to be used`.

If your are running Docker Engine on Linux, listening on this socket should be
[enabled by default](https://docs.docker.com/reference/cli/dockerd/#daemon-socket-option).


### Integration tests

There are also integration tests in `PIXL/test/` directory that can be run using the `PIXL/test/run-system-test.sh`. See the
[integration test docs](test/README.md) for more info.


### Workflow

Before raising a PR, make sure to **run all tests** for each PIXL module
and not just the component you have been working on as this will help us catch unintentional regressions without spending GH actions minutes.


## Linting

For Python development we use [ruff](https://docs.astral.sh/ruff/) and [mypy](https://mypy.readthedocs.io/)
alongside [pytest](https://www.pytest.org/).
There is support (sometimes through plugins) for these tools in most IDEs & editors.


We run [pre-commit](https://pre-commit.com/) as part of the GitHub Actions CI.

To run it locally as a one-off:
```shell
pre-commit run --all-files
```

To install the git pre-commit hook locally so it runs every time you make a commit:
```shell
pre-commit install
```

The `pre-commit` configuration can be found in [`.pre-commit-config.yml`](../../.pre-commit-config.yaml).


## Environment variables

Running the `pixl` pipeline and the tests requires a set of environment variables to be set. The `test/`
directory contains a complete [`.env` file](../../test/.env) that can be used to run the pipeline and tests locally.
Either run any `pixl` commands from the `test/` directory, or copy the `test/.env` file to the root of the repository.

### Secrets

PIXL uses an [Azure Keyvault](../../README.md#project-secrets) to store authentication details for
external services. We have a development keyvault for testing. Access to this keyvault is provided
by a set of environment variables specified in `test/.secrets.env.sample`.
To run the pipeline locally, you will need to copy this file to `test/.secrets.env` and fill out
the necessary values, which can be found in the `pixl-dev-secrets.env` shared LastPass note.
