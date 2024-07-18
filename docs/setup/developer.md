# Developer setup

## Setting up Python virtual environment

### Using conda
```
conda create -n "pixlVE" python=3.10  pip -c conda-forge
conda activate pixlVE
conda list -n pixlVE #to check installed packages
conda deactivate && conda remove -n pixlVE --all #in case you want to remove it
```

### Using python virtual environment
```
# Installing dependencies in Ubuntu 22.04
sudo apt-get install -y python3-pip
sudo apt-get install -y python3-venv
# Create path for venv
cd $HOME
mkdir *VE
cd *VE
# Create virtual environment
python3 -m venv pixlVE
source pixlVE/bin/activate
```

## Installation

You can install all PIXL Python modules by running the following commands from the `PIXL/` directory:

```shell
python -m pip install -e "pixl_core/[dev]"
python -m pip install -e "pytest-pixl/[dev,test]"
python -m pip install -e "pixl_core/[test]"
python -m pip install -e "cli/[dev,test]"
python -m pip install -e "pixl_imaging/[dev,test]"
python -m pip install -e "pixl_dcmd/[dev,test]"
python -m pip install -e "pixl_export/[dev,test]"
python -m pip install -e "hasher/[dev,test]"
```

See each service's README for instructions for individual developing and testing instructions.
Most modules require [`docker`](https://docs.docker.com/desktop/) and `docker-compose` to be installed to run tests.

## Testing

### Module-level testing

Once you have installed each module, you can run the tests for a module using the `pytest` command, e.g.

```shell
cd pixl_core/
pytest
```

Alternatively, you can run most of the module-level tests from the root of the repo with:

```shell
pytest
```

The `pytest.ini` file in the root of the repo contains the configuration for running most of the module-level tests at once.
However, `pixl_dcmd` and `hasher` have `conftests.py` files that clash, so only `pixl_dcmd` is included as a `testpath` in the
top-level `pytest.ini`. You will therefore need to run tests for `hasher` from the `hasher` directory.


### Integration tests

There are also integration tests in `PIXL/test/` directory that can be run using the `PIXL/test/run-system-test.sh`. See the
[integration test docs](test/README.md) for more info.


### Workflow

Before raising a PR, make sure to **run all tests** for each PIXL module
and not just the component you have been working on as this will help us catch unintentional regressions without spending GH actions minutes :-)


## Linting

For Python development we use [ruff](https://docs.astral.sh/ruff/) and [mypy](https://mypy.readthedocs.io/)
alongside [pytest](https://www.pytest.org/).
There is support (sometimes through plugins) for these tools in most IDEs & editors.

Before raising a PR, make sure to **run all tests** for each PIXL module
and not just the component you have been working on as this will help us catch unintentional regressions without spending GH actions minutes :-)

## Linting

We run [pre-commit](https://pre-commit.com/) as part of the GitHub Actions CI. To install and run it locally, do:

```shell
python -m pip install pre-commit
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
