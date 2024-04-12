# Hasher API

_The secure hashing service_.

This package provides a _FastAPI_ service that can be used to generate secure hashes.
It is used by the [PIXL EHR API](../pixl_ehr/README.md) (for EHR anonymisation) and
[PIXL Orthanc Anon](../orthanc/orthanc-anon/README.md) (for DICOM image anonymisation) services.

## Local development

### Dependencies

It is assumed you have a Python virtual environment configured using a tool like `conda` or `venv`.
Install `hasher` locally with:

```shell
pip install -e .
```

### Setup

The hasher API retrieves secret hashing keys and project-specific salts from an Azure Key Vault.
To connect to the key vault, the following environment variables need to be set

```
HASHER_API_AZ_CLIENT_ID
HASHER_API_AZ_CLIENT_PASSWORD
HASHER_API_AZ_TENANT_ID
HASHER_API_AZ_KEY_VAULT_NAME
```

See [below](#azure-setup) for instructions on how to set these up.


### Test

From this directory run:

```bash
pytest
```

---

## Azure setup

See the [Azure Key vault setup](../docs/setup/azure-keyvault.md) documentation for more information.

Save the credentials in `.secrets.env` and a LastPass `Hasher API <environment> secrets` note.

```
HASHER_API_AZ_CLIENT_ID=<generated-app-ID>
HASHER_API_AZ_CLIENT_PASSWORD=<generated-password>
HASHER_API_AZ_TENANT_ID=<tenant-ID>
HASHER_API_AZ_KEY_VAULT_NAME=<key-vault-name>
```
