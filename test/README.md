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

Spinning up the Docker containers requires the `$INFORMDB_PAT` environment variable to be set to a
valid [GitHub Personal Access Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token)
with read access to the [UCLH-Foundry/Inform-DB](https://github.com/UCLH-Foundry/Inform-DB) repo.

1. Create a [fine-grained Personal Access Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token)
   with **read** access to the *UCLH-Foundry/Inform-DB* repo
2. Create `.env.test` with `cp .env.test.sample .env.test`
3. Add your `githb_pat***` token to `.env.test` as `INFORMDB_PAT=***`

Then, run the system test with:

```bash
./run-system-test.sh
```
