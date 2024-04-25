# DICOMweb server

PIXL has the option to upload DICOM files to a DICOMweb server, configured by the `"destination"`
field in the [project config](/README.md#3-configure-a-new-project). This is handled by the
`DicomWebUploader` class in `core.uploader._dicomweb`.

## Configuration

The configuration for the DICOMweb server is controlled by the following environment variables and secrets:

- `"ORTHANC_URL"`: The URL of the Orthanc server from _where_ the upload will happen, this will typically be the `orthanc-anon` instance
- The `"<project_slug>--dicomweb--username"` and `"<project_slug>--dicomweb--password"` for authentication, which are fetched from the [Azure Keyvault](../setup/azure-keyvault.md)
- The `"<project_slug>--dicomweb--url"` to define the DICOMweb endpoint in Orthanc, also fetched from the Azure Keyvault

We dynamically configure the DICOMweb server endpoint in Orthanc (see `core.uploader._dicomweb.DicomWebUploader._setup_dicomweb_credentials()`),
so we can have different (or no) endpoints for different projects.

## Testing setup

For [testing](../../test/README.md) we set up an additional Orthanc server that acts as a DICOMweb server,
using the vanilla Orthanc Docker image with the DICOMWeb plugin enabled.

For more information on using the DICOMweb Orthanc plugin, see the [Orthanc book](https://orthanc.uclouvain.be/book/plugins/dicomweb.html).

