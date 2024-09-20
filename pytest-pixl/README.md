# PIXL pytest plugin

Installable `pytest` plugin module providing common test fixtures used throughout PIXL.

## Installation

```bash
python -m pip install -e ../pixl_core -e ".[test]"
```

## pytest-cov’s engine
```
COV_CORE_SOURCE=src COV_CORE_CONFIG=.coveragerc COV_CORE_DATAFILE=.coverage.eager pytest --cov=src --cov-append
```

## Available fixtures

### `ftps_server`

Spins up an FTPS server with _implicit SSL_ enabled on the local machine. Configurable by setting
the following environment variables:

- `FTP_HOST`: URL to the FTPS server
- `FTP_PORT`: port on which the FTPS server is listening
- `FTP_USER_NAME`: name of user with access to the FTPS server
- `FTP_USER_PASSWORD`: password for the authorised user

## Available testing utilities

- `dicom.write_volume`: write a volume of MRI DICOMs for testing
- `dicom.generate_dicom_dataset`: generate a DICOM dataset for testing

`generate_dicom_dataset()` on its own will generate a DICOM dataset with default values for all tags,
with the default tags defined in [`default_dicom_tags.json`](./src/pytest_pixl/data/default_dicom_tags.json)
(see [Default DICOM tags](#default-dicom-tags) for more details).

Alternatively, you can pass a dictionary of tags to `generate_dicom_dataset()` to override the default values.
Currently we only handle the following dictionary keys

- `instance_creation_time`
- `sop_instance_uid`
- `instance_number`
- `image_position_patient`
- `slice_location`
- `window_centre`
- `window_width`
- `pixel_data`

This is useful for example when generating DICOM datasets for a volume of slices.
See for example `dicom.write_volume()`.

In addition to the tags dictionary, `generate_dicom_dataset()` has a `**kwargs` parameter that
allows you to set any arbitrary DICOM tag. Note, however, that this needs to be a valid DICOM tag, as checked by [`pydicom.datadict.dictionary_has_tag()`](https://pydicom.github.io/pydicom/stable/reference/generated/pydicom.datadict.dictionary_has_tag.html). For example:

```python
generate_dicom_dataset(Manufacturer="cool company", Modality="CT")
```

For [private tags](https://dicom.nema.org/dicom/2013/output/chtml/part05/sect_7.8.html),
use `add_private_tags(ds, private_tags)`, where `ds` is a `pydicom.Dataset`,
and `private_tags` is a list of `tuple`s with the following format:

```
[(tag_id, VR, value), ...]
```

where `tag` can be a `str`, `int` or `Tuple[int, int]`, `VR` is a `str` and `value` is a `str`.
Note that this requires the [VR](https://dicom.nema.org/dicom/2013/output/chtml/part05/sect_6.2.html)
of the tag to be known.

For example, if we want to add the following tags, which are relevant for
[Philips Diffusion images](https://github.com/rordenlab/dcm2niix/tree/master/Philips#diffusion-direction):

```
(2001,1003) FL 1000
(2005,10b0) FL 1.0
(2005,10b1) FL 1.0
(2005,10b2) FL 0.0
```

we could use the following code:

```python
ds = generate_dicom_dataset()
add_private_tags(
    ds,
    [
        ((0x2001, 0x1003), "FL", 1000),
        ((0x2005, 0x10B0), "FL", 1.0),
        ((0x2005, 0x10B1), "FL", 1.0),
        ((0x2005, 0x10B2), "FL", 0.0),
    ],
)
```

## Data

### Default DICOM tags

[`default_dicom_tags.json`](./src/pytest_pixl/data/default_dicom_tags.json) contains a dictionary of
default DICOM tag values used to generate fake DICOM data in `generate_dicom_dataset`.
The JSON file was created by running [`scripts/create_default_dicom_tags_json.py`](./scripts/create_default_dicom_tags_json.py),
with the details implemented in [`pytest_pixl.dicom._create_default_json`](./src/pytest_pixl/dicom.py).

