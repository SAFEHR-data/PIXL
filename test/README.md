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

Run with

```bash
./run-system-test.sh
```
