# PIXL DICOM de-identifier

The `pixl_dcmd` package provides helper functions for de-identifying DICOM data. It is currently
only used by the [`orthanc-anon` plugin](../orthanc/orthanc-anon/plugin/pixl.py).

For external users, the `pixl_dcmd` package provides the following functionality:

- `anonymise_dicom()`: Applies the [anonymisation operations](#tag-scheme-anonymisation) 
   for the appropriate tag scheme using [Kitware Dicom Anonymizer](https://github.com/KitwareMedical/dicom-anonymizer)
   and deletes any tags not mentioned in the tag scheme. The dataset is updated in place.
     - There is also an option to synchronise to the PIXL database, external users can avoid this
   to just run the allow-list and applying the tag scheme.
     - Will throw a `PixlSkipInstanceError` for any series based on the project config file. {SK: this sentence doesn't quite make sense to me} Specifically, an error
       will be thrown if:
       - the series description matches any series in `series_filters` (usually to remove localiser series)
       - the modality of the DICOM is not in `modalities`
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
[SK: Between this and the previous read me I'm not sure this is totally clear, is it possible to have a full example of the yml file linked so that base and a manufacturer_overrides make a bit more sense ]

## 'PIXL/pixl_dcmd' Directory Contents

<details>
<summary>
<h3> Subdirectories with links to the relevant README </h3> 

</summary>

[src](./src/README.md)

[tests](./tests/README.md)

</details>

<details>
<summary>
<h3> Files </h3> 

</summary>

| **Configuration** | **User docs** |
| :--- | :--- |
| pyproject.toml | README.md | 

</details>

