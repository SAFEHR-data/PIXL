# Hasher API

_The secure hashing service_.

This package provides a _FastAPI_ service that can be used to generate secure hashes.
It is used by [PIXL Orthanc Anon](../orthanc/orthanc-anon/README.md) for DICOM image
anonymisation.

The main responsibility of the hasher API is to generate secure hashes of sensitive data. As part
of this, it connects to an Azure Key Vault to retrieve the necessary hashing keys and salts. The
_FastAPI_ service currently provides a single endpoint `/hash`, that accepts a JSON payload with
the project name and message to be hashed. The project name is used to retrieve the project-specific
salt from the key vault. An optional length for the hash can also be provided.

If no salt exists for the project, a new salt is generated and stored in the key vault. This salt is
then used to generate the hash. In addition to the key vault salt, an optional local salt can be set
using the `LOCAL_SALT_VALUE` environment variable.

Finally, the `Hasher` class has a `create_salt()` method that allows users to create and store
a new salt interactively.

## Local development

### Dependencies

It is assumed you have a Python virtual environment configured using a tool like `conda` or `venv`.
Install `hasher` locally with:

```shell
python -m pip install -e .
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

SK QUESTION: is the reference to Last Pass something that is specific to us or is it a dependency somebody else would need. actually I assume the whole Azure thing is rather how we have chosen to do that rather than a necessity for somebody i.e. they might use a different system for storing their hashes

```
HASHER_API_AZ_CLIENT_ID=<generated-app-ID>
HASHER_API_AZ_CLIENT_PASSWORD=<generated-password>
HASHER_API_AZ_TENANT_ID=<tenant-ID>
HASHER_API_AZ_KEY_VAULT_NAME=<key-vault-name>
```

## 'PIXL/hasher' Directory Contents

<details>
<summary>
<h3> Subdirectories with links to the relevant README </h3> 

</summary>

[src](./src/README.md)

[tests](./tests/README.md)

</details>

<details>
<summary>
<h3> Files </h3> 

</summary>

| **Configuration** | **User docs** |
| :--- | :--- |
| pyproject.toml | README.md |

</details>



