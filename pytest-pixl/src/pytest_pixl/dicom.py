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
from typing import Optional

import numpy as np
from pydicom.dataset import Dataset


def write_volume(filename_pattern: str):
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
        ds = generate_dicom_dataset(
            pixel_data=rng.random(size=(256, 256)),
            **slice_info,
        )
        file_name = filename_pattern.format(slice=i)
        ds.save_as(file_name, write_like_original=False)


# Remove the noqa comments once this function takes a sensible number of arguments
def generate_dicom_dataset(  # noqa: PLR0913
    instance_creation_time: str = "180048.910",
    sop_instance_uid: str = "1.3.46.670589.11.38023.5.0.7404.2023012517580650156",
    instance_number: str = "1",
    image_position_patient: tuple[float, float, float] = (76.0, -139.0, 119.0),
    slice_location: float = 82.0,
    window_centre: str = "321",
    window_width: str = "558",
    pixel_data: Optional[np.ndarray] = None,
) -> Dataset:
    """
    Write a single fake DICOM image with customisable tags.

    Elements that vary between slices are exposed as arguments.  Values for
    these can be obtained from the dicom_variables.json file.
    """
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
