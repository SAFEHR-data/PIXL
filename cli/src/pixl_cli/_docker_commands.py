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


# Required to allow passing unkown options to docker-compose
# https://click.palletsprojects.com/en/8.1.x/advanced/#forwarding-unknown-options
@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def dc(args: tuple[str]) -> None:
    """Wrapper around docker compose for PIXL"""
    # Construct the docker-compose arguments based on subcommand
    docker_args = list(args)

    if "up" in args:
        docker_args = _parse_up_args(args)
    if "down" in args:
        docker_args = _check_down_args(args)

    run_docker_compose(docker_args, working_dir=PIXL_ROOT)


def _parse_up_args(args: tuple[str, ...]) -> list:
    """Check up args and set docker compose profile"""
    args_list = list(args)

    up_index = args.index("up")
    external_pixl_db_env = config("EXTERNAL_PIXL_DB", cast=bool)
    args_list[up_index:up_index] = (
        ["--profile", "postgres"] if external_pixl_db_env else ["--profile", "postgres-exposed"]
    )

    args_list.extend(["--wait", "--build", "--remove-orphans"])
    return args_list


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
