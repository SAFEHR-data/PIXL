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

"""Utilities for the system test"""

import json
import shlex
import subprocess
from functools import partial, update_wrapper

from pytest_pixl.helpers import wait_for_condition


def wait_for_stable_orthanc_anon(
    seconds_max: int,
    seconds_interval: int,
    seconds_condition_stays_true_for: int,
    min_instances: int = 3,
) -> None:
    """
    Query the orthanc-anon REST API to check that the correct number of instances
    have been received.
    If they haven't within the time limit, raise a TimeoutError
    """
    instances = []

    def at_least_n_instances(n_instances: int) -> bool:
        nonlocal instances
        instances_cmd = shlex.split(
            "docker exec system-test-orthanc-anon-1 "
            'curl -u "orthanc_anon_username:orthanc_anon_password" '
            "http://orthanc-anon:8042/instances"
        )
        instances_output = subprocess.run(instances_cmd, capture_output=True, check=True, text=True)  # noqa: S603
        instances = json.loads(instances_output.stdout)
        return len(instances) >= n_instances

    condition = partial(at_least_n_instances, min_instances)
    update_wrapper(condition, at_least_n_instances)

    def list_instances() -> str:
        return f"Expecting at least {min_instances} instances.\northanc-anon instances: {instances}"

    wait_for_condition(
        condition,
        seconds_max=seconds_max,
        seconds_interval=seconds_interval,
        progress_string_fn=list_instances,
        seconds_condition_stays_true_for=seconds_condition_stays_true_for,
    )
