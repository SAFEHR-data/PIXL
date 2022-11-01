import os
from pathlib import Path

import pulsar
import pandas as pd
import json

import click
from requests import request, put
from pixl_cli._logging import logger, set_log_level


@click.group()
@click.option("--debug/--no-debug", default=False)
def cli(debug: bool) -> None:
    """Main CLI entrypoint"""
    set_log_level("INFO" if not debug else "DEBUG")


@cli.command()
@click.argument("json_filename", type=click.Path(exists=True))
def create_namespace(json_filename: str) -> None:
    """Create a Pulsar namespace to use in which the topics will be created"""

    if not Path(json_filename).suffix == ".json":
        raise ValueError("Cannot create a namespace. File must be a ,json. "
                         "See: https://pulsar.apache.org/docs/admin-api-namespaces/ ")

    if not queue_is_up():
        raise RuntimeError("Failed to create namespace. Queue admin api not up")

    tenant = os.environ['PIXL_PULSAR_TENANT']
    namespace = os.environ['PIXL_PULSAR_NAMESPACE']
    with open(json_filename, "r") as json_file:
        data = json.load(json_file)

    res = put(
        url=f"{base_pulsar_url()}/namespaces/{tenant}/{namespace}",
        json=data,
        headers={"Content-Type": "application/json"}
    )

    if res.status_code not in (200, 204):
        raise RuntimeError(f"Failed to create namespace:\n {res} {res.text}")


@cli.command()
@click.argument("csv_filename", type=click.Path(exists=True))
@click.option(
    "--no-restart",
    is_flag=True,
    show_default=True,
    default=False,
    help="Do not restart from a saved state. Otherwise will use "
    "<topic-name>.csv files if they are present to rebuild the state.",
)
def populate(csv_filename: str, no_restart: bool) -> None:
    """
    Create the PIXL driver by populating the queues and setting the rate parameters
    for the token buckets
    """
    logger.info(f"Populating queue from {csv_filename}")

    all_messages = messages_from_csv(Path(csv_filename))
    for topic_name in (
        os.environ["PIXL_PULSAR_EHR_TOPIC_NAME"],
        os.environ["PIXL_PULSAR_PACS_TOPIC_NAME"],
    ):
        cached_state_filepath = state_filepath_for_topic(topic_name)
        if cached_state_filepath.exists() and not no_restart:
            messages = Messages.from_state_file(cached_state_filepath)
        else:
            messages = all_messages

        messages.send(topic_name)


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
    "--only-ehr",
    is_flag=True,
    show_default=True,
    default=False,
    help="Only stop running EHR queries, leaving PACS to process",
)
@click.option(
    "--only-pacs",
    is_flag=True,
    show_default=True,
    default=False,
    help="Only stop running PACS queries, leaving EHR to process",
)
def stop(only_ehr: bool, only_pacs: bool) -> None:
    """
    Stop extracting images and/or EHR data. Will consume all messages present on the
    EHR and PACS queue topics and save them to a .csv file
    """

    if only_ehr and only_pacs:
        raise ValueError(
            "only-ehr and only-pacs arguments are mutually exclusive. " "Use only one"
        )

    stop_ehr_extraction = not only_pacs
    stop_pacs_extraction = not only_ehr

    logger.info(
        f"Stopping extraction of {'EHR' if stop_ehr_extraction else ''}"
        f" {'PACS' if stop_pacs_extraction else ''}"
    )

    for topic_name in (
        os.environ["PIXL_PULSAR_EHR_TOPIC_NAME"],
        os.environ["PIXL_PULSAR_PACS_TOPIC_NAME"],
    ):
        consume_all_messages_and_save_csv_file(topic_name)


def create_client() -> pulsar.Client:
    return pulsar.Client(
        f"pulsar://{os.environ['PIXL_PULSAR_HOST']}"
        f":{os.environ['PIXL_PULSAR_BINARY_PORT']}"
    )


def consume_all_messages_and_save_csv_file(
    topic_name: str, timeout_in_seconds: int = 1
) -> None:

    client = create_client()
    consumer = client.subscribe(
        topic_name, subscription_name=f"subscriber-{topic_name}"
    )

    while True:
        try:
            msg = consumer.receive(timeout_millis=int(1000 * timeout_in_seconds))
        except:  # noqa
            logger.info(
                f"Spent 1s waiting for more messages. "
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


def state_filepath_for_topic(topic_name: str) -> Path:
    return Path(f"{topic_name}.state")


class Messages(list):

    @classmethod
    def from_state_file(cls, filepath: Path) -> "Messages":

        assert filepath.exists() and filepath.suffix == ".state"

        return cls(open(filepath, "r").readlines())

    def send(self, topic_name: str) -> None:
        logger.debug(f"Sending {len(self)} messages to topic {topic_name}")

        client = create_client()
        tenant  = os.environ['PIXL_PULSAR_TENANT']
        namespace = os.environ['PIXL_PULSAR_NAMESPACE']
        producer = client.create_producer(
            f"{tenant}/{namespace}/{topic_name}",
            block_if_queue_full=True
        )

        for message in self:
            producer.send(message.encode("utf-8"))

        client.close()


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


def base_pulsar_url():
    return (f"http://{os.environ['PIXL_PULSAR_HOST']}:"
            f"{os.environ['PIXL_PULSAR_HTTP_PORT']}/admin/v2")


def queue_is_up() -> bool:
    res = request("GET", f"{base_pulsar_url()}/brokers/health")
    return res.status_code == 200
