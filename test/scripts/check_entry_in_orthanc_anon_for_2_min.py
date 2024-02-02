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
After pixl has run this script will query the orthanc-anon REST API to check
that the correct number of instances have been received.

Because we have to wait for a stable study, poll for 2 minutes
"""

import json
import shlex
import subprocess
from time import sleep

SECONDS_WAIT = 5

# Check for two minutes that the instances have been received in orthanc anon
instances = []
for seconds in range(0, 121, SECONDS_WAIT):
    instances_cmd = shlex.split('docker exec system-test-orthanc-anon-1 curl -u "orthanc_anon_username:orthanc_anon_password" http://orthanc-anon:8042/instances')
    instances_output = subprocess.run(instances_cmd, capture_output=True, check=True, text=True)
    instances = json.loads(instances_output.stdout)
    print("orthanc-anon instances:", instances)
    if len(instances) == 2:
        break
    sleep(SECONDS_WAIT)

assert len(instances) == 2
