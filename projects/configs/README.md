# Project configurations for PIXL extractions

This directory contains:

- Configuration files for specific projects, including automated test cases, these reference the the sub-directories for their anonymisation rules. These are copied from [template_config.yaml](/template_config.yaml). Expand the [Setup PIXL in GAE section](/README.md#setup-pixl-in-gae) of the main readme find the `Configure a new project` section for more information
- [image-operations](./image-operations/): Methods for removing identifiable information from the pixel data of DICOM data
- [tag-operations](./tag-operations/): Allowlist for each DICOM tag. All projects are expected to use [tag-operations/base.yaml](./tag-operations/base.yaml), adding in extra configurations for each modality. Any DICOM tag not defined will be removed in anonymisation. 
- In some cases, [tag-operations/manufacturer-overrides/](./tag-operations/manufacturer-overrides/) will be defined private DICOM tags are required from a manufacturer.