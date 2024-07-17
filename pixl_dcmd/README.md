# PIXL DICOM de-identifier

The `pixl_dcmd` package provides helper functions for de-identifying DICOM data. It is currently
only used by the [`orthanc-anon` plugin](../orthanc/orthanc-anon/plugin/pixl.py).

The reason for having this as a separate package instead of having the functionality in `pixl_core`
is because `orthanc` requires Python 3.9, whereas the rest of PIXL is on 3.10 or higher.

Specifically, the `pixl_dcmd` package provides the following functionality:

- `anonymise_dicom()`: Applies the [anonymisation operations](#tag-scheme-anonymisation) for the appropriate tag scheme using [Kitware Dicom Anonymizer](https://github.com/KitwareMedical/dicom-anonymizer)) and deletes any tags not mentioned in the tag scheme.
- `write_dataset_to_bytes()`: writes a DICOM dataset to a bytes object

## Installation

Install the Python dependencies with

```bash
python -m pip install -e ../pixl_core/ -e ".[test,dev]"
```

## Test

```bash
pytest
```

## Tag scheme anonymisation

The tag schemes for anonymisation are taken from the YAML files defined in the
[project configuration](../README.md#the-config-YAML-file). This should include at least a `base`,
and optionally a `manufacturer_overrides`.

If a `manufacturer_overrides` is defined, it will be used to override the `base` tags, if the
manufacturer of the DICOM file matches the manufacturer in the `manufacturer_overrides`. Any tags
in the `manufacturer_overrides` that are not in the `base` will be added to the scheme as well.
