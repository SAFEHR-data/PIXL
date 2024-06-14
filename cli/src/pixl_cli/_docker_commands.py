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
from decouple import config
from loguru import logger

PIXL_ROOT = Path(__file__).parents[3].resolve()

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
@docker_env_option
@docker_extra_args
def up(env_file: list[Path], *, extra_args: tuple[str]) -> None:
    """Start all the PIXL services"""
    # Construct the docker-compose arguments
    docker_args = ["up", "--wait", "--build", "--remove-orphans", *extra_args]
    run_docker_compose(env_file, docker_args, working_dir=PIXL_ROOT)


# Required to allow passing unkown options to docker-compose
# https://click.palletsprojects.com/en/8.1.x/advanced/#forwarding-unknown-options
@click.command(context_settings={"ignore_unknown_options": True})
@docker_env_option
@docker_extra_args
def down(env_file: list[Path], *, extra_args: tuple[str, ...]) -> None:
    """Stop all the PIXL services"""
    if config("ENV") == "prod" and "--volumes" in extra_args:
        click.secho("WARNING: Attempting to remove volumes in production.", fg="yellow")
        if not click.confirm("Are you sure you want to remove the volumes?"):
            click.secho("Running 'docker compose down' without removing volumes.", fg="blue")
            extra_args = tuple(arg for arg in extra_args if arg != "--volumes")

    # Construct the docker-compose arguments
    docker_args = ["down", *extra_args]
    run_docker_compose(env_file, docker_args, working_dir=PIXL_ROOT)


def run_docker_compose(env_file: list[Path], args: list, working_dir: Optional[Path]) -> None:
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
        # env_file will be a list of paths, so we need to flatten it
        *[f"--env-file={f}" for f in env_file],
        *args,
    ]
    logger.debug("Running docker compose with: {}, from {}", docker_args, working_dir)

    subprocess.run(docker_args, check=True, cwd=working_dir)  # noqa: S603
