# The PIXL database

PIXL uses a [postgres database](../../postgres/README.md) to

- Add hashed identifiers along with the originals for DICOM images (in `pixl_dcmd`)
- Keep track of the export status of imaging (in `core.uploader`) studies and the projects they are used in

Note that the pipeline will not process any studies for a project that have already been exported.
