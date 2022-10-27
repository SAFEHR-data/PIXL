import os
import click
import pulsar
import pandas as pd

from pathlib import Path
from pixl_driver._logging import logger, set_log_level


@click.group()
@click.option("--debug/--no-debug", default=False)
def cli(debug):

    set_log_level("INFO" if not debug else "DEBUG")


@cli.command()
@click.argument("csv_filename", type=click.Path(exists=True))
@click.option(
    "--pacs-rate",
    type=int,
    default=5,
    help="Rate at which images are requested from PACS in images per second",
)
@click.option(
    "--ehr-rate",
    type=int,
    default=20,
    help="Rate at which EHR is requested from EMAP in queries per second",
)
@click.option(
    "--no-restart",
    is_flag=True,
    show_default=True,
    default=False,
    help="Do not restart from a saved state. Otherwise will use "
    "<topic-name>.csv files if they are present to rebuild the state.",
)
def up(csv_filename: Path, pacs_rate: int, ehr_rate: int, no_restart: bool) -> None:
    """
    Create the PIXL driver by populating the queues and setting the rate parameters
    for the token buckets
    """
    logger.info(
        f"Populating queue from {csv_filename}. Using {pacs_rate} images/s "
        f"and {ehr_rate} EHR queries/second"
    )

    all_messages = messages_from_csv(csv_filename)
    for topic_name in (
        os.environ["PIXL_PULSAR_EHR_TOPIC_NAME"],
        os.environ["PIXL_PULSAR_PACS_TOPIC_NAME"],
    ):
        state_filepath = state_filepath_for_topic(topic_name)
        if state_filepath.exists() and not no_restart:
            messages = Messages(open(state_filepath, "r").readlines())
        else:
            messages = all_messages

        messages.send(topic_name)


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
        except:
            logger.info(
                f"Spent 1s waiting for more messages. "
                f"Stopping subscriber for {topic_name}"
            )
            break

        try:
            with open(state_filepath_for_topic(topic_name), "r") as csv_file:
                print(msg.value(), file=csv_file)

            consumer.acknowledge(msg)
        except:
            consumer.negative_acknowledge(msg)

    client.close()
    return None


def state_filepath_for_topic(topic_name: str) -> Path:
    return Path(f"{topic_name}.txt")


class Messages(list):
    def send(self, topic_name: str) -> None:
        client = create_client()
        producer = client.create_producer(topic_name, block_if_queue_full=True)

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

    df = pd.read_csv(filepath, header=1)  # First line is column names
    messages = Messages()

    if not list(df.columns[:4]) != expected_col_names:
        raise ValueError(
            f"csv file expected to have at least {expected_col_names} as "
            f"column names"
        )

    mrn_col_name, acc_num_col_name, _, datetime_col_name = expected_col_names
    for row in df.iterrows():
        messages.append(
            f"{row[mrn_col_name]},"
            f"{row[acc_num_col_name]},"
            f"{row[datetime_col_name]}"
        )

    return messages
