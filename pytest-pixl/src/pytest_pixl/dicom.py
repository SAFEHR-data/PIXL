#  Copyright (c) University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Functions to write test DICOM files."""

from __future__ import annotations

import importlib
import json
from typing import Any, TypeAlias, Union

import numpy as np
from pydicom.datadict import dictionary_has_tag
from pydicom.dataset import Dataset


def write_volume(filename_pattern: str) -> None:
    """
    Write a volume's worth of fake DICOM images

    Args:
        filename_pattern: The pattern to use for the filenames. This should
        include a {slice} which will be replaced with the slice number e.g.
        /tmp/slice{slice:03d}.dcm

    """
    # volume_dicom_variables.json contains per slice information for a 3D image (geometry,
    # windowing, etc.)
    dicom_variables_path = importlib.resources.files("pytest_pixl").joinpath(
        "data/volume_dicom_variables.json"
    )
    variables = json.loads(dicom_variables_path.open("r").read())
    rng = np.random.default_rng(0)
    for i, slice_info in enumerate(variables):
        slice_info["pixel_data"] = rng.random(size=(256, 256))
        ds = generate_dicom_dataset(slice_info)
        file_name = filename_pattern.format(slice=i)
        ds.save_as(file_name, write_like_original=False)


TAGS_DICT = {
    "instance_creation_time": "180048.910",
    "sop_instance_uid": "1.3.46.670589.11.38023.5.0.7404.2023012517580650156",
    "instance_number": "1",
    "image_position_patient": (76.0, -139.0, 119.0),
    "slice_location": 82.0,
    "window_centre": "321",
    "window_width": "558",
    "pixel_data": None,
}


def generate_dicom_dataset(tag_values: dict = TAGS_DICT, **kwargs) -> Dataset:
    """
    Write a single fake DICOM image with customisable tags.

    Elements that vary between slices are exposed as arguments.  Values for
    these can be obtained from the dicom_variables.json file.

    :param tag_values: A dictionary of tag values to use for the DICOM image. Uses a default set of
        tags if not provided.
    :param kwargs: Additional tags to set in the DICOM image. These need to be valid DICOM tags.
        E.g. generate_dicom_dataset(Manufacturer="cool company", Modality="CT")
    :return: A pydicom Dataset object representing the DICOM image.
    :raises ValueError: If an invalid DICOM tag is provided.
    """
    instance_creation_time = tag_values["instance_creation_time"]
    sop_instance_uid = tag_values["sop_instance_uid"]
    instance_number = tag_values["instance_number"]
    image_position_patient = tag_values["image_position_patient"]
    slice_location = tag_values["slice_location"]
    window_centre = tag_values["window_centre"]
    window_width = tag_values["window_width"]
    pixel_data = tag_values["pixel_data"]

    if pixel_data is None:
        pixel_data = np.zeros((256, 256))

    ds = _generate_default_dicom_dataset()
    ds.InstanceCreationTime = instance_creation_time
    ds.SOPInstanceUID = sop_instance_uid

    # Referenced Performed Procedure Step Sequence: Referenced Performed Procedure Step 1
    ds.ReferencedPerformedProcedureStepSequence[0].InstanceNumber = instance_number

    ds.ImagePositionPatient = list(image_position_patient)
    ds.SliceLocation = slice_location
    ds.WindowCenter = window_centre
    ds.WindowWidth = window_width
    ds.PixelData = pixel_data.tobytes()

    # Handle any additional tags
    for key, value in kwargs.items():
        # Check if tag is DICOM compliant
        if dictionary_has_tag(key):
            setattr(ds, key, value)
        else:
            msg = f"Tag {key} is not a valid DICOM tag"
            raise ValueError(msg)

    return ds


def _generate_default_dicom_dataset() -> Dataset:
    """
    Write a single fake DICOM image, with default values taken from
    data/defualt_dicom_tags.json.
    """
    default_variables_path = importlib.resources.files("pytest_pixl").joinpath(
        "data/default_dicom_tags.json"
    )
    variables = json.loads(default_variables_path.open("r").read())
    ds = Dataset.from_json(variables)
    # Not sure why these weren't carried over to the JSON
    ds.is_implicit_VR = True
    ds.is_little_endian = True
    return ds


# Type alias for a DICOM tag
Tag: TypeAlias = tuple[Union[int, str, tuple[int, int]], str, Any]


def add_private_tags(ds: Dataset, private_tags: list[Tag]) -> None:
    """
    Add private tags to an existing DICOM dataset.

    This uses pydicom.Dataset.private_block

    :param ds: The DICOM dataset to add the private tags to.
    :type ds: pydicom.Dataset
    :param private_tags: A list of custom tags to add to the DICOM dataset. Each tag should be a
        tuple of the form (tag_id, VR, value).
    :type private_tags: list[tuple[Union[int, str, tuple[int, int]], str, Any]]
    """
    for tag_id, vr, value in private_tags:
        ds.add_new(tag_id, vr, value)
