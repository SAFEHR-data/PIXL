#!/usr/bin/env python3

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

"""
We need to test that orthanc-raw is enforcing the configured maximum storage
limit.  This script will upload sufficient instances to orthanc-raw that the
maximum storage capacity will be reached and then confirm that the original test
images are no longer stored.

Polling to allow for orthanc processing time.
"""
import logging
import tempfile
from pathlib import Path
from time import sleep

import pytest
import requests
from decouple import config
from pytest_pixl.dicom import write_volume

SECONDS_WAIT = 5

raw_instances_url = "http://localhost:{}/instances".format(config("ORTHANC_RAW_WEB_PORT"))


@pytest.mark.usefixtures("_setup_pixl_cli")
def test_max_storage_in_orthanc_raw():
    """
    This checks that orthanc-raw acknowledges the configured maximum storage size
    ./scripts/check_max_storage_in_orthanc_raw.sh
    Run this last because it will force out original test images from orthanc-raw
    ./scripts/test_max_storage_in_orthanc_raw.py
    """
    # Check we have the 2 instances expected from insert_test_data.sh
    for seconds in range(0, 121, SECONDS_WAIT):
        original_instances = requests.get(
            raw_instances_url,
            auth=(config("ORTHANC_RAW_USERNAME"), config("ORTHANC_RAW_PASSWORD")),
            timeout=10,
        ).json()
        logging.info(
            "Waited for %s seconds, orthanc-raw instances: %s", seconds, original_instances
        )
        if len(original_instances) == 2:
            break
        sleep(SECONDS_WAIT)
    assert len(original_instances) == 2

    # Upload enough new instances to exceed the configured max storage of orthanc-raw
    with tempfile.TemporaryDirectory() as temp_dir:
        write_volume(temp_dir + "/dcm{slice:03d}.dcm")
        n_dcm = 0
        for dcm in Path(temp_dir).glob("*.dcm"):
            # We use data= rather than files= in this request because orthanc does not return JSON
            # when files= is used.
            with dcm.open("rb") as dcm_fh:
                upload_response = requests.post(
                    raw_instances_url,
                    auth=(config("ORTHANC_RAW_USERNAME"), config("ORTHANC_RAW_PASSWORD")),
                    data=dcm_fh,
                    timeout=10,
                )
            if upload_response.status_code != requests.codes.ok:
                # orthanc will eventually refuse more instances because the test
                # exam we're using exceeds the max storage
                if upload_response.json()["OrthancError"] == "The file storage is full":
                    # This is what we're looking for when storage limit reached
                    break
                # Something else happened preventing the upload
                err_str = f"Failed to upload {dcm} to orthanc-raw"
                raise RuntimeError(err_str)
            n_dcm += 1
        logging.info("Uploaded %s new instances", n_dcm)

    # Check the instances in orthanc-raw to see if the original instances have been removed
    for seconds in range(0, 121, SECONDS_WAIT):
        new_instances = requests.get(
            raw_instances_url,
            auth=(config("ORTHANC_RAW_USERNAME"), config("ORTHANC_RAW_PASSWORD")),
            timeout=10,
        ).json()
        logging.info(
            "Waited for %s seconds, orthanc-raw contains %s instances", seconds, len(new_instances)
        )
        if any(instance in new_instances for instance in original_instances):
            sleep(SECONDS_WAIT)
        else:
            logging.info("Original instances have been removed from orthanc-raw")
            break

    assert not any(instance in new_instances for instance in original_instances)
