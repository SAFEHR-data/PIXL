# PIXL DICOM de-identifier

The `pixl_dcmd` package provides helper functions for de-identifying DICOM data. It is currently
only used by the [`orthanc-anon` plugin](../orthanc/orthanc-anon/plugin/pixl.py).

The reason for having this as a separate package instead of having the functionality in `pixl_core`
is because `orthanc` requires Python 3.9, whereas the rest of PIXL is on 3.10 or higher.

Specifically, the `pixl_dcmd` package provides the following functionality:

- `remove_overlays()`: searches for [DICOM overlay
  planes](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.9.2.html) and
  removes them
- `apply_tag_scheme()`: applies the anonymisation operations for a given tag scheme
- `enforce_whitelist()`: deletes all tags that are not in the tagging scheme
- `write_dataset_to_bytes()`: writes a DICOM dataset to a bytes object

## Installation

Install the Python dependencies with

```bash
pip install -e ../pixl_core/ -e .[test,dev]
```

## Test

```bash
pytest
```
