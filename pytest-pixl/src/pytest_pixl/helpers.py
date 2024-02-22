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
"""Testing utilities"""
import logging
import subprocess
from pathlib import Path


def run_subprocess(
    cmd: list[str], working_dir: Path, *, shell=False, timeout=360
) -> subprocess.CompletedProcess[bytes]:
    """
    Run a command but capture the stderr and stdout better than the CalledProcessError
    string representation does
    """
    logging.info("Running command %s", cmd)
    try:
        cp = subprocess.run(
            cmd,
            check=True,
            cwd=working_dir,
            shell=shell,  # noqa: S603 input is trusted
            timeout=timeout,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exception:
        logging.error("*** exception occurred running: '%s'", cmd)  # noqa: TRY400 will raise anyway
        logging.error("*** stdout:\n%s", exception.stdout.decode())  # noqa: TRY400
        logging.error("*** stderr:\n%s", exception.stderr.decode())  # noqa: TRY400
        raise
    else:
        logging.info("Success, returncode = %s", cp.returncode)
        logging.info("stdout =\n%s", cp.stdout.decode())
        logging.info("stderr =\n%s", cp.stderr.decode())
        return cp
