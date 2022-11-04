import click
from pixl_cli.main import start, update


@start.command("pacs")
@click.option(
    "--rate",
    type=int,
    default=5,
    help="Rate at which images are requested from PACS in images per second",
)
def start_ehr_extraction(rate: int) -> None:
    """Start PACS extraction"""
    raise NotImplementedError


@update.command("pacs")
@click.option(
    "--rate",
    type=int,
    required=True,
    help="Rate at which images are requested from PACS in images per second",
)
def update_pacs_rate(rate: int) -> None:
    raise NotImplementedError
