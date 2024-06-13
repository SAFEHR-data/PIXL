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

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from loguru import logger


def run_docker_compose(
    project: str, env_file: Path, args: list, working_dir: Optional[Path]
) -> None:
    """Wrapper to run docker-compose through the CLI."""
    docker_compose_cmd = shutil.which("docker-compose")

    if not docker_compose_cmd:
        err_msg = "docker-compose not found in $PATH. Please make sure it's installed."
        raise FileNotFoundError(err_msg)

    docker_args = [
        docker_compose_cmd,
        "--project-name",
        project,
        "--env-file",
        str(env_file),
        *args,
    ]
    logger.debug("Running docker-compose with: {}, from {}", docker_args, working_dir)

    subprocess.run(docker_args, check=True, cwd=working_dir)  # noqa: S603
