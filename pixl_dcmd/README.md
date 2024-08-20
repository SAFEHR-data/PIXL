# PIXL DICOM de-identifier

The `pixl_dcmd` package provides helper functions for de-identifying DICOM data. It is currently
only used by the [`orthanc-anon` plugin](../orthanc/orthanc-anon/plugin/pixl.py).

For external users, the `pixl_dcmd` package provides the following functionality:

- `anonymise_dicom()`: Applies the [anonymisation operations](#tag-scheme-anonymisation) 
   for the appropriate tag scheme using [Kitware Dicom Anonymizer](https://github.com/KitwareMedical/dicom-anonymizer)
   and deletes any tags not mentioned in the tag scheme.
   There is also an option to synchronise to the PIXL database, external users can avoid this
   to just run the allow-list and applying the tag scheme. 
- `anonymise_and_validate_dicom()`: Compares DICOM validation issues before and after calling `anonymise_dicom`
  and returns a dictionary of the new issues. Can also avoid synchronising with PIXL database

## Installation

Install the Python dependencies from the `pixl_dcmd` directory:

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
