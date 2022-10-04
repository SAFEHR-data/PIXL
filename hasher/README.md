# Hasher API


_The secure hashing service_

## Azure setup
 ***WIP***
### Step 1
Create Service Principal & grant access as per
https://learn.microsoft.com/en-gb/dotnet/api/overview/azure/Security.KeyVault.Secrets-readme

### Step 2
Set env:
export AZURE_CLIENT_ID="<appId>"
export AZURE_CLIENT_SECRET="<password>"
export AZURE_TENANT_ID="<tenantID>"

### Step 3
KeyVault URI
https://uclhdif-sandbox-vault.vault.azure.net/

----


## Local development
### Dependencies 
It is assumed you have a Python virtual environment configured using a tool like Conda or pyenv.  
Install the dependencies from inside the _PIXL/hasher/src_ directory:
```bash
pip install -r requirements.txt
```

### Setup
Create a _local.env_ file in _PIXL.hasher/src/hasher_ from _local.env.sample_ in the same location.

### Run
from the _PIXL/hasher/src_ directory:
```bash
uvicorn hasher.main:app --host=0.0.0.0 --port=8000 --reload
```

### Test
from the _PIXL/hasher/src_ directory:
```bash
bin/run-tests.sh
```
or
```bash
PIXL_ENV=test pytest --ff hasher/tests
```
to skip linting and run only the last failed test.

----
