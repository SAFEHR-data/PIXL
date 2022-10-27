import click

from pixl_driver._logging import logger, set_log_level


@click.group()
@click.option('--debug/--no-debug', default=False)
def main(debug):

    set_log_level("INFO" if not debug else "DEBUG")


@main.command()
@click.argument("csv_filename", type=click.Path(exists=True))
@click.option("--pacs-rate", type=int, default=5,
              help="Rate at which images are requested from PACS in images per second")
@click.option("--ehr-rate", type=int, default=20,
              help="Rate at which EHR is requested from EMAP in queries per second")
def up(csv_filename: str, pacs_rate: int, ehr_rate: int) -> None:
    logger.info(f'Populating queue from {csv_filename}. Using {pacs_rate} images/s '
                f'and {ehr_rate} EHR queries/second')

    # TODO: parse csv, add to queue, import token buckets


@main.command()
@click.option("--only-ehr", is_flag=True, show_default=True, default=False,
              help="Only stop running EHR queries, leaving PACS to process")
@click.option("--only-pacs", is_flag=True, show_default=True, default=False,
              help="Only stop running PACS queries, leaving EHR to process")
def stop(only_ehr: bool, only_pacs: bool) -> None:

    if only_ehr and only_pacs:
        raise ValueError("only-ehr and only-pacs arguments are mutually exclusive. "
                         "Use only one")

    stop_ehr = not only_pacs
    stop_pacs = not only_ehr

    logger.info(f"Stopping extraction of {'EHR' if stop_ehr else ''}"
                f" {'PACS' if stop_pacs else ''}")

    # TODO: set token buckets to zero
