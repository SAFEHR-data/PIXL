# Hasher API

_The secure hashing service_.

This package provides a _FastAPI_ service that can be used to generate secure hashes. It is used by
the [PIXL EHR API](../pixl_export/README.md) (for EHR anonymisation) and
[PIXL Orthanc Anon](../orthanc_anon/README.md) (for DICOM image anonymisation) services.

## Local development

### Dependencies

It is assumed you have a Python virtual environment configured using a tool like Conda or pyenv.
Install the dependencies from inside the _PIXL/hasher/src_ directory:

```bash
pip install -e .
```

### Setup

Create a _local.env_ file in _PIXL.hasher/src/hasher_ from _local.env.sample_ in the same location.
Use the credentials stored in the `Hasher API dev secrets` note in LastPass to populate the
environment variables. Set `LOG_ROOT_DIR` to anywhere convenient.

### Run

from the _PIXL/hasher/src_ directory:

```bash
uvicorn hasher.main:app --host=0.0.0.0 --port=8000 --reload
```

### Test

From this directory run:

```bash
pytest
```

---

<details><summary>Azure setup</summary>

## Azure setup

_This is done for the \_UCLH_DIF_ `dev` tenancy, will need to be done once in the _UCLHAZ_ `prod`
tenancy when ready to deploy to production.\_

An Azure Key Vault is required to hold the secret key used in the hashing process. This Key Vault
and secret must persist any infrastructure changes so should be separate from disposable
infrastructure services. ServicePrincipal is required to connect to the Key Vault.

The application uses the ServicePrincipal and password to authenticates with Azure via environment
variables. See
[here](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.environmentcredential?view=azure-python)
for more info.

The Key Vault and ServicePrincipal have already been created for the `dev` environment and details
are stored in the `Hasher API dev secrets` note in the shared FlowEHR folder on LastPass.

The process for doing so using the `az` CLI tool is described below. This can be converted into a
Terraform template but given that we need a single, permanent instance of this, having a repeatable
template is less useful.

This process must be repeated for `staging` & `prod` environments.

### Step 1

Create the Azure Key Vault in an appropriate resource group:

```bash
az keyvault create --resource-group <resource-group-name> --name <key-vault-name> --location "UKSouth"
```

### Step 2

Create Service Principal & grant access as per

```bash
az ad sp create-for-rbac -n hasher-api --skip-assignment
```

This will produce the following output

```json
{
    "appId": "<generated-app-ID>",
    "displayName": "<app-name>",
    "name": "http://<app-name>",
    "password": "<generated-password>",
    "tenant": "<tenant-ID>"
}
```

### Step 3

Assign correct permissions to the newly created ServicePrincipal

```bash
az keyvault set-policy --name <key-vault-name> --spn <generated-app-ID> --secret-permissions backup delete get list set
```

### Step 4

Create a secret and store in the Key Vault

Use Python to create a secret:

```python
import secrets
secrets.token_urlsafe(32)
```

copy the secret and paste as <secret-value> below

```bash
az keyvault secret set --vault-name "<key-vault-name>" --name "<secret-name>" --value "<secret-value>"
```

### Step 5

Save credentials in `.env` and a LastPass `Hasher API <environment> secrets` note.

```
HASHER_API_AZ_CLIENT_ID=<generated-app-ID>
HASHER_API_AZ_CLIENT_PASSWORD=<generated-password>
HASHER_API_AZ_TENANT_ID=<tenant-ID>
HASHER_API_AZ_KEY_VAULT_NAME=<key-vault-name>
HASHER_API_AZ_KEY_VAULT_SECRET_NAME=<secret-name>
```

</details>
