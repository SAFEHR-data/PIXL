import click
from pixl_cli.main import config, logger, start, update
from requests import post


@start.command("ehr")
@click.option(
    "--rate",
    type=int,
    default=20,
    help="Rate at which EHR is requested from EMAP in queries per second",
)
def start_ehr_extraction(rate: int) -> None:
    """Start EHR extraction"""

    if rate == 0:
        raise RuntimeError("Cannot start EHR with extract rate of 0. Must be >0")

    _update_ehr_extract_rate(rate)


@update.command("ehr")
@click.option(
    "--rate",
    type=int,
    required=True,
    help="Rate at which EHR is requested from EMAP in queries per second",
)
def update_ehr_rate(rate: int) -> None:
    _update_ehr_extract_rate(rate)


def _update_ehr_extract_rate(rate: int) -> None:
    logger.info("Updating the EHR extraction rate")

    base_url = f"http://{config['ehr_api']['host']}:{config['ehr_api']['port']}"
    response = post(url=f"{base_url}/token-bucket-refresh-rate", json={"rate": rate})

    if response.status_code == 200:
        logger.info(
            "Successfully updated EHR extraction, with a "
            f"rate of {rate} queries/second"
        )

    else:
        raise RuntimeError(f"Failed to start EHR extraction: {response}")
