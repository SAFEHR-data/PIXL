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
This script will upload additional instances to orthanc-raw and then confirm
that the original test images have been removed.

Polling to allow for orthanc processing time.
"""

from pathlib import Path
import tempfile
from time import sleep

from dotenv import dotenv_values

import requests

from write_fake_dicoms import write_volume

SECONDS_WAIT = 5

config = dotenv_values(".env.test")
raw_instances_url = "http://localhost:{0}/instances".format(
    config["ORTHANC_RAW_WEB_PORT"]
)

# Check we have the 2 instances expected from insert_test_data.sh
for seconds in range(0, 121, SECONDS_WAIT):
    original_instances = requests.get(
        raw_instances_url,
        auth=(config["ORTHANC_RAW_USERNAME"], config["ORTHANC_RAW_PASSWORD"]),
    ).json()
    print(f"Waited for {seconds} seconds, orthanc-raw instances: {original_instances}")
    if len(original_instances) == 2:
        break
    sleep(SECONDS_WAIT)
assert len(original_instances) == 2

# Upload enough new instances to exceed the configured max storage of orthanc-raw
with tempfile.TemporaryDirectory() as temp_dir:
    write_volume(temp_dir + "/dcm{slice:03d}.dcm")
    n_dcm = 0
    for dcm in Path(temp_dir).glob("*.dcm"):
        upload_response = requests.post(
            raw_instances_url,
            auth=(config["ORTHANC_RAW_USERNAME"], config["ORTHANC_RAW_PASSWORD"]),
            files={"file": open(dcm, "rb")},
        )
        if upload_response.status_code != 200:
            # orthanc will eventually refuse more instances becuase the test
            # exam we're using exceeds the max storage
            break
        n_dcm += 1
    print(f"Uploaded {n_dcm} new instances")

# Check the instances in orthanc-raw to see if the original instances have been removed
for seconds in range(0, 121, SECONDS_WAIT):
    new_instances = requests.get(
        raw_instances_url,
        auth=(config["ORTHANC_RAW_USERNAME"], config["ORTHANC_RAW_PASSWORD"]),
    ).json()
    print(
        "Waited for {seconds} seconds, orthanc-raw contains {n_instances} instances".format(
            seconds=seconds, n_instances=len(new_instances)
        )
    )
    if any([instance in new_instances for instance in original_instances]):
        sleep(SECONDS_WAIT)
    else:
        print("Original instances have been removed from orthanc-raw")
        break

assert not any([instance in new_instances for instance in original_instances])
