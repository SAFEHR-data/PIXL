# PIXL DICOM de-identifier

The `pixl_dcmd` package provides helper functions for de-identifying DICOM data. It is currently
only used by the [`orthanc-anon` plugin](../orthanc/orthanc-anon/plugin/pixl.py).

For external users, the `pixl_dcmd` package provides the following functionality:

- `anonymise_dicom()`: Applies the [anonymisation operations](#tag-scheme-anonymisation) 
   for the appropriate tag scheme using [Kitware Dicom Anonymizer](https://github.com/KitwareMedical/dicom-anonymizer)
   and deletes any tags not mentioned in the tag scheme. The dataset is updated in place.
     - There is also an option to synchronise to the PIXL database, external users can avoid this
   to just run the allow-list and applying the tag scheme.
     - Will throw a PixlDiscardError for any series based on the project config file. 
       - Series description matches `series_filters` (usually to remove localiser series) 
       - Modality of the DICOM is not in `modalities`
- `anonymise_and_validate_dicom()`: Compares DICOM validation issues before and after calling `anonymise_dicom`
  and returns a dictionary of the new issues. Can also avoid synchronising with PIXL database

```python
import pathlib
import pydicom

from pixl_dcmd import anonymise_and_validate_dicom

dataset_path = pydicom.data.get_testdata_file(
    "MR-SIEMENS-DICOM-WithOverlays.dcm", download=True
)
config_path = pathlib.Path(__file__).parents[2] / "projects/configs/test-extract-uclh-omop-cdm.yaml"
# updated inplace
dataset = pydicom.dcmread(dataset_path)
validation_issues = anonymise_and_validate_dicom(dataset, config_path=config_path, synchronise_pixl_db=False)
assert validation_issues == {}
assert dataset != pydicom.dcmread(dataset_path)
```


## Installation

Install the Python dependencies from the `pixl_dcmc` directory:

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
