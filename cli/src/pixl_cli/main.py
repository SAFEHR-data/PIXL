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
"""PIXL command line interface functionality"""

import json
import os
from operator import attrgetter
from pathlib import Path
from typing import Any, Optional

import click
import requests
import yaml
from core.patient_queue.producer import PixlProducer
from core.patient_queue.subscriber import PixlBlockingConsumer

from ._io import copy_public_parquet_and_build_messages, messages_from_state_file
from ._logging import logger, set_log_level
from ._utils import clear_file, remove_file_if_it_exists


def _load_config(filename: str = "pixl_config.yml") -> dict:
    """CLI configuration generated from a .yaml file"""
    if not Path(filename).exists():
        msg = f"Failed to find {filename}. It must be present " f"in the current working directory"
        raise OSError(msg)

    with Path(filename).open() as config_file:
        config_dict = yaml.safe_load(config_file)
    return dict(config_dict)


config = _load_config()

# localhost needs to be added to the NO_PROXY environment variables on GAEs
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "localhost"


@click.group()
@click.option("--debug/--no-debug", default=False)
def cli(*, debug: bool) -> None:
    """PIXL command line interface"""
    set_log_level("WARNING" if not debug else "DEBUG")


@cli.command()
@click.option(
    "--queues",
    default="ehr,pacs",
    show_default=True,
    help="Comma seperated list of queues to populate with messages generated from the "
    "input file(s)",
)
@click.option(
    "--restart/--no-restart",
    show_default=True,
    default=True,
    help="Restart from a saved state. Otherwise will use the given input file(s)",
)
@click.argument(
    "parquet-dir", required=True, type=click.Path(path_type=Path, exists=True, file_okay=False)
)
def populate(parquet_dir: Path, *, restart: bool, queues: str) -> None:
    """
    Populate a (set of) queue(s) from a parquet file directory

    PARQUET-DIR: Directory containing the public and private parquet input files and an
        extract_summary.json log file.
        It's expected that the directory structure will be:

            PARQUET-DIR
            ├── private
            │   ├── PERSON_LINKS.parquet
            │   └── PROCEDURE_OCCURRENCE_LINKS.parquet
            ├── public
            │   └── PROCEDURE_OCCURRENCE.parquet
            └── extract_summary.json
    """
    logger.info(f"Populating queue(s) {queues} from {parquet_dir}")
    messages = copy_public_parquet_and_build_messages(parquet_dir)

    for queue in queues.split(","):
        state_filepath = state_filepath_for_queue(queue)
        if state_filepath.exists() and restart:
            logger.info(f"Extracting messages from state: {state_filepath}")
            inform_user_that_queue_will_be_populated_from(state_filepath)
            messages = messages_from_state_file(state_filepath)

        remove_file_if_it_exists(state_filepath)  # will be stale

        with PixlProducer(queue_name=queue, **config["rabbitmq"]) as producer:
            producer.publish(sorted(messages, key=attrgetter("study_datetime")))


@cli.command()
@click.option(
    "--queues",
    default="ehr,pacs",
    show_default=True,
    help="Comma seperated list of queues to start consuming from",
)
@click.option(
    "--rate",
    type=float,
    default=None,
    help="Rate at which to process items from a queue (in items per second)."
    "If None then will use the default rate defined in the config file",
)
def start(queues: str, rate: Optional[int]) -> None:
    """Start consumers for a set of queues"""
    if rate == 0:
        msg = "Cannot start extract with a rate of 0. Must be >0"
        raise RuntimeError(msg)

    _start_or_update_extract(queues=queues.split(","), rate=rate)


@cli.command()
@click.option(
    "--queues",
    default="ehr,pacs",
    show_default=True,
    help="Comma seperated list of queues to update the consume rate of",
)
@click.option(
    "--rate",
    type=float,
    required=True,
    help="Rate at which to process items from a queue (in items per second)",
)
def update(queues: str, rate: Optional[float]) -> None:
    """Update one or a list of consumers with a defined rate"""
    _start_or_update_extract(queues=queues.split(","), rate=rate)


def _start_or_update_extract(queues: list[str], rate: Optional[float]) -> None:
    """Start or update the rate of extraction for a list of queue names"""
    for queue in queues:
        _update_extract_rate(queue_name=queue, rate=rate)


def _update_extract_rate(queue_name: str, rate: Optional[float]) -> None:
    logger.info("Updating the extraction rate")

    api_config = api_config_for_queue(queue_name)

    if rate is None:
        if api_config.default_rate is None:
            msg = (
                "Cannot update the rate for %s. No default rate was specified.",
                queue_name,
            )
            raise ValueError(msg)
        rate = float(api_config.default_rate)
        logger.info(f"Using the default extract rate of {rate}/second")

    logger.debug(f"POST {rate} to {api_config.base_url}")

    response = requests.post(
        url=f"{api_config.base_url}/token-bucket-refresh-rate",
        json={"rate": rate},
        timeout=10,
    )

    success_code = 200
    if response.status_code == success_code:
        logger.info("Successfully updated EHR extraction, with a " f"rate of {rate} queries/second")

    else:
        runtime_error_msg = (
            "Failed to update rate on consumer for %s: %s",
            queue_name,
            response,
        )
        raise RuntimeError(runtime_error_msg)


@cli.command()
@click.option(
    "--queues",
    default="ehr,pacs",
    show_default=True,
    help="Comma seperated list of queues to consume messages from",
)
def stop(queues: str) -> None:
    """
    Stop extracting images and/or EHR data. Will consume all messages present on the
    queues and save them to a file
    """
    logger.info(f"Stopping extraction of {queues}")

    for queue in queues.split(","):
        logger.info(f"Consuming messages on {queue}")
        consume_all_messages_and_save_csv_file(queue_name=queue)


@cli.command()
def kill() -> None:
    """Stop all the PIXL services"""
    os.system("docker compose stop")  # noqa: S605,S607


@cli.command()
@click.option(
    "--queues",
    default="ehr,pacs",
    show_default=True,
    help="Comma seperated list of queues to consume messages from",
)
def status(queues: str) -> None:
    """Get the status of the PIXL consumers"""
    for queue in queues.split(","):
        logger.info(f"[{queue:^10s}] refresh rate = ", _get_extract_rate(queue))


@cli.command()
def az_copy_ehr() -> None:
    """Copy the EHR data to azure"""
    api_config = api_config_for_queue("ehr")
    response = requests.get(url=f"{api_config.base_url}/az-copy-current", timeout=10)

    success_code = 200
    if response.status_code != success_code:
        msg = f"Failed to run az copy due to: {response.text}"
        raise RuntimeError(msg)


def _get_extract_rate(queue_name: str) -> str:
    """
    Get the extraction rate in items per second from a queue

    :param queue_name: Name of the queue to get the extract rate for (e.g. ehr)
    :return: The extract rate in items per seconds

    Throws a RuntimeError if the status code is not 200.
    """
    api_config = api_config_for_queue(queue_name)
    success_code = 200
    try:
        response = requests.get(url=f"{api_config.base_url}/token-bucket-refresh-rate", timeout=10)
        if response.status_code != success_code:
            msg = (
                "Failed to get the extract rate for %s due to: %s",
                queue_name,
                response.text,
            )
            raise RuntimeError(msg)
        return str(json.loads(response.text)["rate"])

    except (ConnectionError, AssertionError):
        logger.error(f"Failed to get the extract rate for {queue_name}")
        return "unknown"


def consume_all_messages_and_save_csv_file(queue_name: str, timeout_in_seconds: int = 5) -> None:
    """Consume all messages and write them out to a CSV file"""
    logger.info(
        f"Will consume all messages on {queue_name} queue and timeout after "
        f"{timeout_in_seconds} seconds"
    )

    with PixlBlockingConsumer(queue_name=queue_name, **config["rabbitmq"]) as consumer:
        state_filepath = state_filepath_for_queue(queue_name)
        if consumer.message_count > 0:
            logger.info("Found messages in the queue. Clearing the state file")
            clear_file(state_filepath)

        consumer.consume_all(state_filepath)


def state_filepath_for_queue(queue_name: str) -> Path:
    """Get the filepath to the queue state"""
    return Path(f"{queue_name.replace('/', '_')}.state")


def queue_is_up() -> Any:
    """Checks if the queue is up"""
    with PixlProducer(queue_name="") as producer:
        return producer.connection_open


def inform_user_that_queue_will_be_populated_from(path: Path) -> None:  # noqa: D103
    _ = input(
        f"Found a state file *{path}*. Please use --no-restart if this and other "
        f"state files should be ignored, or delete this file to ignore. Press "
        f"Ctrl-C to exit and any key to continue"
    )


class APIConfig:
    """
    Class to represent the configuration for an API

    Attributes
    ----------
    host : str
        Hostname for the API
    port : int
        Port for the API
    default_rate : int
        Default rate for the API

    Methods
    -------
    base_url()
        Return the base url for the API
    """

    def __init__(self, kwargs: dict) -> None:
        """Initialise the APIConfig class"""
        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self.default_rate: Optional[int] = None

        self.__dict__.update(kwargs)

    @property
    def base_url(self) -> str:
        """Return the base url for the API"""
        return f"http://{self.host}:{self.port}"


def api_config_for_queue(queue_name: str) -> APIConfig:
    """Configuration for an API associated with a queue"""
    config_key = f"{queue_name}_api"

    if config_key not in config:
        msg = (
            f"Cannot update the rate for {queue_name}. {config_key} was"
            f" not specified in the configuration"
        )
        raise ValueError(msg)

    return APIConfig(config[config_key])
