# PIXL DICOM de-identifier

The `pixl_dcmd` package provides helper functions for de-identifying DICOM data. It is currently
only used by the [`orthanc-anon` plugin](../orthanc/orthanc-anon/plugin/pixl.py).

For external users, the `pixl_dcmd` package provides the following functionality:

- `anonymise_dicom()`: Applies the [anonymisation operations](#tag-scheme-anonymisation) 
   for the appropriate tag scheme using [Kitware Dicom Anonymizer](https://github.com/KitwareMedical/dicom-anonymizer)
   and deletes any tags not mentioned in the tag scheme. The dataset is updated in place.
     - Will throw a `PixlSkipInstanceError` for any series based on the project config file. Specifically, an error
       will be thrown if:
       - the series description matches any series in `series_filters` (usually to remove localiser series)
       - the modality of the DICOM is not in `modalities`
- `anonymise_and_validate_dicom()`: Compares DICOM validation issues before and after calling `anonymise_dicom`
  and returns a dictionary of the new issues

```python
import os
import pathlib
import pydicom

from core.project_config.pixl_config_model import load_config_and_validate
from pixl_dcmd import anonymise_and_validate_dicom

config_dir = pathlib.Path().cwd().parents[2] / "projects" / "configs"
config_path = config_dir / "test-external-user.yaml"
os.environ["PROJECT_CONFIGS_DIR"] = config_dir.as_posix()  # needed to validate config
config = load_config_and_validate(config_path)

dataset_path = pydicom.data.get_testdata_file(
    "MR-SIEMENS-DICOM-WithOverlays.dcm", download=True,
)
dataset = pydicom.dcmread(dataset_path)

# the dataset is updated inplace
validation_issues = anonymise_and_validate_dicom(dataset, config=config)
assert validation_issues == {}
assert dataset != pydicom.dcmread(dataset_path)
```

## Installation

Install the Python dependencies from the `pixl_dcmd` directory:

```bash
uv sync
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

## 'PIXL/pixl_dcmd' Directory Contents

### Subdirectories

[src](./src/README.md)

[tests](./tests/README.md)

### Files

pyproject.toml

README.md

