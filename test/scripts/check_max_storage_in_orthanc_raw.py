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

import json
from pathlib import Path
import shlex
import subprocess
import tempfile
from time import sleep

from write_fake_dicoms import write_volume

SECONDS_WAIT = 5

# Check we have the 2 instances expected from insert_test_data.sh
instances_cmd = shlex.split('docker exec system-test-orthanc-raw-1 curl -u "orthanc_raw_username:orthanc_raw_password" http://orthanc-raw:8042/instances')
for seconds in range(0, 121, SECONDS_WAIT):
    original_instances_output = subprocess.run(instances_cmd, capture_output=True, check=True, text=True)
    original_instances = json.loads(original_instances_output.stdout)
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
        upload_cmd = shlex.split(f'curl -X POST -u "orthanc_raw_username:orthanc_raw_password" http://localhost:7005/instances --data-binary @"{dcm}"')
        upload_output = subprocess.run(upload_cmd, check=True, capture_output=True, text=True)
        upload_response = json.loads(upload_output.stdout)
        print(upload_response)
        if upload_response.get("Status") != "Success":
            break
        n_dcm += 1
    print(f"Uploaded {n_dcm} new instances")

# Check the instances in orthanc-raw to see if the original instances have been removed
for seconds in range(0, 121, SECONDS_WAIT):
    new_instances_output = subprocess.run(instances_cmd, capture_output=True, check=True, text=True)
    new_instances = json.loads(new_instances_output.stdout)
    print(f"Waited for {seconds} seconds, orthanc-raw instances: {new_instances}")
    if original_instances[0] in new_instances:
        sleep(SECONDS_WAIT)
    elif original_instances[1] in new_instances:
        sleep(SECONDS_WAIT)
    else:
        break

for instance in original_instances:
    assert instance not in new_instances