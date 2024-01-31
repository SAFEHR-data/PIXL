#!/usr/bin/env python3

# After pixl has run this script will query the orthanc-anon REST API to check
# that the correct number of instances have been received.

import json
import shlex
import subprocess


instances_cmd = shlex.split('docker exec -it system-test-orthanc-anon-1 curl -u "orthanc_anon_username:orthanc_anon_password" http://orthanc-anon:8042/instances')
instances_output = subprocess.run(instances_cmd, capture_output=True, check=True, text=True)
instances = json.loads(instances_output.stdout)
print("orthanc-anon instances:", instances)
assert len(instances) == 2
