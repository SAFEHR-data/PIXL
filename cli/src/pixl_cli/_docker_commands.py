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

import click
from loguru import logger

ALLOWED_PROJECT_NAMES = ["pixl_dev", "pixl_test", "pixl_prod"]
PIXL_ROOT = Path(__file__).parents[3].resolve()

docker_project_option = click.option(
    "-p",
    "--project",
    type=click.Choice(ALLOWED_PROJECT_NAMES, case_sensitive=False),
    default="pixl_dev",
    show_default=True,
    help="Project to run the service for",
)
docker_env_option = click.option(
    "--env-file",
    type=click.Path(exists=True),
    multiple=True,
    default=[".env"],
    show_default=True,
    help="Path to the .env file to use with docker compose",
)
docker_extra_args = click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)


# Required to allow passing unkown options to docker-compose
# https://click.palletsprojects.com/en/8.1.x/advanced/#forwarding-unknown-options
@click.command(context_settings={"ignore_unknown_options": True})
@docker_project_option
@docker_env_option
@docker_extra_args
def up(project: str, env_file: Path, *, extra_args: list) -> None:
    """Start all the PIXL services"""
    # Construct the docker-compose arguments
    docker_args = ["up", "--wait", "--detach", "--build", "--remove-orphans", *extra_args]
    run_docker_compose(project, env_file, docker_args, working_dir=PIXL_ROOT)


# Required to allow passing unkown options to docker-compose
# https://click.palletsprojects.com/en/8.1.x/advanced/#forwarding-unknown-options
@click.command(context_settings={"ignore_unknown_options": True})
@docker_project_option
@docker_env_option
@docker_extra_args
def down(project: str, env_file: Path, *, extra_args: list) -> None:
    """Stop all the PIXL services"""
    # Construct the docker-compose arguments
    docker_args = ["down", *extra_args]
    run_docker_compose(project, env_file, docker_args, working_dir=PIXL_ROOT)


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
