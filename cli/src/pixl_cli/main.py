import os
import yaml
from pathlib import Path

import pulsar
import pandas as pd
import json

import click
from requests import request, put
from pixl_cli._logging import logger, set_log_level


def _load_config(filename: str = "pixl_config.yml") -> dict:
    """CLI configuration generated from a .yaml"""
    with open(filename, "r") as config_file:
        config_dict = yaml.load(config_file, Loader=yaml.FullLoader)
    return config_dict


config = _load_config()


@click.group()
@click.option("--debug/--no-debug", default=False)
def cli(debug: bool) -> None:
    """Main CLI entrypoint"""
    set_log_level("INFO" if not debug else "DEBUG")


@cli.command()
@click.argument("json_filename", type=click.Path(exists=True))
@click.option(
    "--name",
    show_default=True,
    default="pixl",
    help="Apache Pulsar namespace. See: "
         "https://pulsar.apache.org/docs/admin-api-namespaces/"
)
@click.option(
    "--tenant",
    show_default=True,
    default="public",
    help="Apache Pulsar tenant to create the namespace under. See: "
         "https://pulsar.apache.org/docs/concepts-multi-tenancy/"
)
def create_namespace(json_filename: str, name: str, tenant: str) -> None:
    """Create a Pulsar namespace to use in which the topics will be created"""

    if not Path(json_filename).suffix == ".json":
        raise ValueError("Cannot create a namespace. File must be a ,json. "
                         "See: https://pulsar.apache.org/docs/admin-api-namespaces/ ")

    if not queue_is_up():
        raise RuntimeError("Failed to create namespace. Queue admin api not up")

    with open(json_filename, "r") as json_file:
        data = json.load(json_file)

    res = put(
        url=f"{base_pulsar_admin_url()}/namespaces/{tenant}/{name}",
        json=data,
        headers={"Content-Type": "application/json"}
    )

    if res.status_code not in (200, 204):
        raise RuntimeError(f"Failed to create namespace:\n {res} {res.text}")


@cli.command()
@click.argument("csv_filename", type=click.Path(exists=True))
@click.option(
    "--topics",
    default="public/pixl/ehr,public/pixl/pacs",
    show_default=True,
    help="Comma seperated list of topics to populate with messages generated from the "
         ".csv file. In the format <tenant>/<namespace>/<topic>",
)
@click.option(
    "--no-restart",
    is_flag=True,
    show_default=True,
    default=False,
    help="Do not restart from a saved state. Otherwise will use "
    "<topic-name>.csv files if they are present to rebuild the state.",
)
def populate(csv_filename: str, topics: str, no_restart: bool) -> None:
    """
    Create the PIXL driver by populating the queues and setting the rate parameters
    for the token buckets
    """
    logger.info(f"Populating queue from {csv_filename}")

    all_messages = messages_from_csv(Path(csv_filename))
    for topic in topics.split(","):

        cached_state_filepath = state_filepath_for_topic(topic)
        if cached_state_filepath.exists() and not no_restart:
            messages = Messages.from_state_file(cached_state_filepath)
        else:
            messages = all_messages

        logger.info(f"Sending {len(messages)} messages")
        messages.send(topic)


@cli.group()
def start() -> None:
    """Start a consumer"""


@start.command()
@click.option(
    "--rate",
    type=int,
    default=5,
    help="Rate at which images are requested from PACS in images per second",
)
def pacs(rate: int) -> None:
    """Start PACS extraction"""
    raise NotImplementedError


@start.command()
@click.option(
    "--ehr-rate",
    type=int,
    default=20,
    help="Rate at which EHR is requested from EMAP in queries per second",
)
def ehr(rate: int) -> None:
    """Start EHR extraction"""
    raise NotImplementedError


@cli.command()
@click.option(
    "--topics",
    default="public/pixl/ehr,public/pixl/pacs",
    show_default=True,
    help="Comma seperated list of topics to consume messages from. In the format "
         "<tenant>/<namespace>/<topic>",
)
def stop(topics: str) -> None:
    """
    Stop extracting images and/or EHR data. Will consume all messages present on the
    topics and save them to a file
    """
    logger.info(f"Stopping extraction of {topics}")

    for topic in topics.split(","):
        consume_all_messages_and_save_csv_file(topic)


def create_client() -> pulsar.Client:
    return pulsar.Client(
        f"pulsar://{config['pulsar']['host']}:{config['pulsar']['binary_port']}"
    )


def consume_all_messages_and_save_csv_file(
    topic_name: str, timeout_in_seconds: int = 10
) -> None:

    client = create_client()
    consumer = client.subscribe(
        f"persistent://{topic_name}", subscription_name=f"subscriber-{topic_name}"
    )

    while True:
        try:
            msg = consumer.receive(timeout_millis=int(1000 * timeout_in_seconds))
            print(msg)
        except:  # noqa
            logger.info(
                f"Spent {timeout_in_seconds}s waiting for more messages. "
                f"Stopping subscriber for {topic_name}"
            )
            break

        try:
            with open(state_filepath_for_topic(topic_name), "r") as csv_file:
                print(msg.value(), file=csv_file)

            consumer.acknowledge(msg)
        except:  # noqa
            consumer.negative_acknowledge(msg)

    client.close()


def state_filepath_for_topic(topic: str) -> Path:
    return Path(f"{topic.replace('/', '_')}.state")


class Messages(list):

    @classmethod
    def from_state_file(cls, filepath: Path) -> "Messages":

        assert filepath.exists() and filepath.suffix == ".state"

        return cls(open(filepath, "r").readlines())

    def send(self, topic: str) -> None:
        logger.debug(f"Sending {len(self)} messages to topic {topic}")

        client = create_client()
        producer = client.create_producer(topic)

        for message in self:
            producer.send(message.encode("utf-8"))

        client.close()
        logger.info(f"Sent {len(self)} messages")


def messages_from_csv(filepath: Path) -> Messages:

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
    messages = Messages()

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


def base_pulsar_admin_url():
    return f"http://{config['pulsar']['host']}:{config['pulsar']['admin_port']}/admin/v2"


def queue_is_up() -> bool:
    res = request("GET", f"{base_pulsar_admin_url()}/brokers/health")
    return res.status_code == 200
