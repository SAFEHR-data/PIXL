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
import json
import os
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd

import click
from patient_queue.producer import PixlProducer
from pixl_cli._logging import logger, set_log_level
from pixl_cli._utils import clear_file, string_is_non_empty
import requests
import yaml


def _load_config(filename: str = "pixl_config.yml") -> dict:
    """CLI configuration generated from a .yaml file"""

    if not Path(filename).exists():
        raise IOError(
            f"Failed to find {filename}. It must be present "
            f"in the current working directory"
        )

    with open(filename, "r") as config_file:
        config_dict = yaml.load(config_file, Loader=yaml.FullLoader)
    return dict(config_dict)


config = _load_config()


@click.group()
@click.option("--debug/--no-debug", default=False)
def cli(debug: bool) -> None:
    """PIXL command line interface"""
    set_log_level("WARNING" if not debug else "DEBUG")


@cli.command()
@click.argument("csv_filename", type=click.Path(exists=True))
@click.option(
    "--queues",
    default="ehr,pacs",
    show_default=True,
    help="Comma seperated list of queues to populate with messages generated from the "
    ".csv file",
)
@click.option(
    "--restart/--no-restart",
    show_default=True,
    default=True,
    help="Restart from a saved state. Otherwise will use <queue-name>.csv file",
)
def populate(csv_filename: str, queues: str, restart: bool) -> None:
    """Populate a (set of) queue(s) from a csv file"""
    logger.info(f"Populating queue(s) {queues} from {csv_filename}")

    for queue in queues.split(","):
        with create_pixl_producer(queue=queue) as producer:
            cached_state_filepath = state_filepath_for_queue(queue)
            if cached_state_filepath.exists() and restart:
                messages = messages_from_state(cached_state_filepath, producer=producer)
            else:
                messages = messages_from_csv(Path(csv_filename), producer=producer)

            logger.info(f"Sending {len(messages)} messages")
            messages.send()


def create_pixl_producer(queue: str) -> PixlProducer:
    """
    Create producer with config information.
    :param queue: Queue the producer should be created for. However, can also be none.
    :returns: Created producer for message publishing to RabbitMQ
    """
    print(config)
    return PixlProducer(
        host=config["rabbitmq"]["host"],
        port=config["rabbitmq"]["port"],
        queue_name=queue,
        user=config["rabbitmq"]["rabbit_user"],
        password=config["rabbitmq"]["rabbit_pw"],
    )


def messages_from_state(filepath: Path, producer: PixlProducer) -> "Messages":
    """Extract a set of messages from a 'state' file"""
    logger.info(f"Extracting messages from state: {filepath}")

    inform_user_that_queue_will_be_populated_from(filepath)
    messages = Messages(producer=producer).from_state_file(filepath)
    os.remove(filepath)

    return messages


@cli.command()
@click.option(
    "--queues",
    default="ehr,pacs",
    show_default=True,
    help="Comma seperated list of queues to start consuming from",
)
@click.option(
    "--rate",
    type=int,
    default=None,
    help="Rate at which to process items from a queue (in items per second)."
    "If None then will use the default rate defined in the config file",
)
def start(queues: str, rate: Optional[int]) -> None:
    """Start consumers for a set of queues"""

    if rate == 0:
        raise RuntimeError("Cannot start extract with a rate of 0. Must be >0")

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
    type=int,
    required=True,
    help="Rate at which to process items from a queue (in items per second)",
)
def update(queues: str, rate: Optional[int]) -> None:
    """Update one or a list of consumers with a defined rate"""
    _start_or_update_extract(queues=queues.split(","), rate=rate)


def _start_or_update_extract(queues: List[str], rate: Optional[int]) -> None:
    """Start or update the rate of extraction for a list of queue names"""

    for queue in queues:
        _update_extract_rate(queue_name=queue, rate=rate)


def _update_extract_rate(queue_name: str, rate: Optional[int]) -> None:
    logger.info("Updating the extraction rate")

    api_config = api_config_for_queue(queue_name)

    if rate is None:
        assert api_config.default_rate is not None
        rate = int(api_config.default_rate)
        logger.info(f"Using the default extract rate of {rate}/second")

    logger.debug(f"POST {rate} to {api_config.base_url}")

    response = requests.post(
        url=f"{api_config.base_url}/token-bucket-refresh-rate", json={"rate": rate}
    )

    if response.status_code == 200:
        logger.info(
            "Successfully updated EHR extraction, with a "
            f"rate of {rate} queries/second"
        )

    else:
        raise RuntimeError(
            f"Failed to update rate on consumer for {queue_name}: {response}"
        )


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
    os.system("docker compose stop")


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
        print(f"[{queue:^10s}] refresh rate = ", _get_extract_rate(queue))


@cli.command()
def az_copy_ehr() -> None:
    """Copy the EHR data to azure"""

    api_config = api_config_for_queue("ehr")
    response = requests.get(url=f"{api_config.base_url}/az-copy-current")

    if response.status_code != 200:
        raise RuntimeError(f"Failed to run az copy due to: {response.text}")


def _get_extract_rate(queue_name: str) -> str:
    """Get the extraction rate in items per second from a queue"""

    api_config = api_config_for_queue(queue_name)

    try:
        response = requests.get(url=f"{api_config.base_url}/token-bucket-refresh-rate")
        assert response.status_code == 200
        return str(json.loads(response.text)["rate"])

    except (ConnectionError, AssertionError):
        logger.error(f"Failed to get the extract rate for {queue_name}")
        return "unknown"


def consume_all_messages_and_save_csv_file(
    queue_name: str, timeout_in_seconds: int = 5
) -> None:
    logger.info(
        f"Will consume all messages on {queue_name} queue and timeout after "
        f"{timeout_in_seconds} seconds"
    )

    with create_pixl_producer(queue=queue_name) as producer:
        if producer.queue.method.message_count > 0:
            logger.info("Found messages in the queue. Clearing the state file")
            clear_file(state_filepath_for_queue(queue_name))

        producer.consume_all(state_filepath_for_queue(producer.queue))


def state_filepath_for_queue(queue_name: str) -> Path:
    return Path(f"{queue_name.replace('/', '_')}.state")


class Messages(list):
    def __init__(self, producer: PixlProducer):
        """
        Initialisation of RabbitMQ service connection.
        :param producer: Producer used for publishing messages.
        """
        self._producer = producer

    @classmethod
    def from_state_file(cls, filepath: Path) -> "Messages":
        logger.info(f"Creating messages from {filepath}")
        assert filepath.exists() and filepath.suffix == ".state"

        return cls(
            [
                line
                for line in open(filepath, "r").readlines()
                if string_is_non_empty(line)
            ]
        )

    def send(self) -> None:
        self._producer.publish(self)
        logger.info(f"Sent {len(self)} messages")


def messages_from_csv(filepath: Path, producer: PixlProducer) -> Messages:
    """Reads patient information from CSV and transforms that into messages.
    :param filepath: Path for CSV file to be read
    :param producer: Producer that will be used to publish to patient queue
    """
    expected_col_names = [
        "VAL_ID",
        "ACCESSION_NUMBER",
        "STUDY_INSTANCE_UID",
        "STUDY_DATE",
    ]
    logger.debug(
        f"Extracting messages from {filepath}. Expecting columns to include "
        f"{expected_col_names}"
    )

    df = pd.read_csv(filepath, header=0, dtype=str)  # First line is column names
    messages = Messages(producer=producer)

    if list(df.columns)[:4] != expected_col_names:
        raise ValueError(
            f"csv file expected to have at least {expected_col_names} as "
            f"column names"
        )

    mrn_col_name, acc_num_col_name, _, datetime_col_name = expected_col_names
    for _, row in df.iterrows():
        messages.append(
            f"{row[mrn_col_name]},"
            f"{row[acc_num_col_name]},"
            f"{row[datetime_col_name]}"
        )

    if len(messages) == 0:
        raise ValueError(f"Failed to find any messages in {filepath}")

    logger.debug(f"Created {len(messages)} messages from {filepath}")
    return messages


def queue_is_up() -> Any:
    with create_pixl_producer(queue="") as producer:
        return producer.connection.is_open


def inform_user_that_queue_will_be_populated_from(path: Path) -> None:
    _ = input(
        f"Found a state file *{path}*. Please use --no-restart if this and other "
        f"state files should be ignored, or delete this file to ignore. Press "
        f"Ctrl-C to exit and any key to continue"
    )


class APIConfig:
    def __init__(self, kwargs: dict):
        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self.default_rate: Optional[int] = None

        self.__dict__.update(kwargs)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def api_config_for_queue(queue_name: str) -> APIConfig:
    """Configuration for an API associated with a queue"""

    config_key = f"{queue_name}_api"

    if config_key not in config:
        raise ValueError(
            f"Cannot update the rate for {queue_name}. {config_key} was"
            f" not specified in the configuration"
        )

    return APIConfig(config[config_key])
