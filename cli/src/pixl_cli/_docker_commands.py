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

from pixl_cli._config import PIXL_ROOT, config


# Required to allow passing unkown options to docker-compose
# https://click.palletsprojects.com/en/8.1.x/advanced/#forwarding-unknown-options
@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def dc(args: tuple[str]) -> None:
    """Wrapper around docker compose for PIXL"""
    # Construct the docker-compose arguments based on subcommand
    docker_args = list(args)

    if "up" in args:
        docker_args = [*args, "--wait", "--build", "--remove-orphans"]
    if "down" in args:
        docker_args = _check_down_args(args)

    run_docker_compose(docker_args, working_dir=PIXL_ROOT)


def _check_down_args(args: tuple[str, ...]) -> list:
    """Stop all the PIXL services"""
    if config("ENV") == "prod" and "--volumes" in args:
        click.secho("WARNING: Attempting to remove volumes in production.", fg="yellow")
        if not click.confirm("Are you sure you want to remove the volumes?"):
            click.secho("Running 'docker compose down' without removing volumes.", fg="blue")
            return [arg for arg in args if arg != "--volumes"]
    return list(args)


def run_docker_compose(args: list, working_dir: Optional[Path]) -> None:
    """Wrapper to run docker-compose through the CLI."""
    docker_cmd = shutil.which("docker")

    if not docker_cmd:
        err_msg = "docker not found in $PATH. Please make sure it's installed."
        raise FileNotFoundError(err_msg)

    pixl_env = config("ENV")

    docker_args = [
        docker_cmd,
        "compose",
        "--project-name",
        f"pixl_{pixl_env}",
        *args,
    ]
    logger.info("Running docker compose with: {}, from {}", docker_args, working_dir)

    subprocess.run(docker_args, check=True, cwd=working_dir)  # noqa: S603
