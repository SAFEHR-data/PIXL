"""Reading and writing files from PIXL CLI."""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from core.omop import OmopExtract
from core.patient_queue.message import Message, deserialise

from pixl_cli._logging import logger
from pixl_cli._utils import string_is_non_empty

# instance of omop extract, can be overriden during testing
extract = OmopExtract()


def messages_from_state_file(filepath: Path) -> list[Message]:
    """
    Return messages from a state file path

    :param filepath: Path for state file to be read
    :return: A list of Message objects containing all the messages from the state file
    """
    logger.info(f"Creating messages from {filepath}")
    if not filepath.exists():
        raise FileNotFoundError
    if filepath.suffix != ".state":
        msg = f"Invalid file suffix for {filepath}. Expected .state"
        raise ValueError(msg)

    return [
        deserialise(line) for line in Path.open(filepath).readlines() if string_is_non_empty(line)
    ]


def messages_from_parquet(dir_path: Path) -> list[Message]:
    """
    Reads patient information from parquet files within directory structure
    and transforms that into messages.
    :param dir_path: Path for parquet directory containing private and public
    files
    """
    public_dir = dir_path / "public"
    private_dir = dir_path / "private"
    log_file = dir_path / "extract_summary.json"

    cohort_data = _check_and_parse_parquet(log_file, private_dir, public_dir)

    expected_col_names = [
        "PrimaryMrn",
        "AccessionNumber",
        "person_id",
        "procedure_date",
        "procedure_occurrence_id",
    ]
    logger.debug(
        f"Extracting messages from {dir_path}. Expecting columns to include "
        f"{expected_col_names}"
    )

    for col in expected_col_names:
        if col not in list(cohort_data.columns):
            msg = (
                f"parquet files are expected to have at least {expected_col_names} as "
                f"column names"
            )
            raise ValueError(msg)

    (
        mrn_col_name,
        acc_num_col_name,
        _,
        dt_col_name,
        procedure_occurrence_id,
    ) = expected_col_names

    omop_es_timestamp, project_name_slug = _parse_log_and_copy_parquet(dir_path, log_file)

    messages = []

    for _, row in cohort_data.iterrows():
        # Create new dict to initialise message
        message = Message(
            mrn=row[mrn_col_name],
            accession_number=row[acc_num_col_name],
            study_datetime=row[dt_col_name],
            procedure_occurrence_id=row[procedure_occurrence_id],
            project_name=project_name_slug,
            omop_es_timestamp=omop_es_timestamp,
        )
        messages.append(message)

    if len(messages) == 0:
        msg = f"Failed to find any messages in {dir_path}"
        raise ValueError(msg)

    logger.info(f"Created {len(messages)} messages from {dir_path}")
    return messages


def _check_and_parse_parquet(log_file: Path, private_dir: Path, public_dir: Path) -> pd.DataFrame:
    for d in [public_dir, private_dir]:
        if not d.is_dir():
            err_str = f"{d} must exist and be a directory"
            raise NotADirectoryError(err_str)
    if not log_file.is_file():
        err_str = f"{log_file} must exist and be a file"
        raise FileNotFoundError(err_str)
    # MRN in people.PrimaryMrn:
    people = pd.read_parquet(private_dir / "PERSON_LINKS.parquet")
    # accession number in accessions.AccessionNumber
    accessions = pd.read_parquet(private_dir / "PROCEDURE_OCCURRENCE_LINKS.parquet")
    # study_date is in procedure.procedure_date
    procedure = pd.read_parquet(public_dir / "PROCEDURE_OCCURRENCE.parquet")
    # joining data together
    people_procedures = people.merge(procedure, on="person_id")
    return people_procedures.merge(accessions, on="procedure_occurrence_id")


def _parse_log_and_copy_parquet(dir_path: Path, log_file: Path) -> tuple[datetime, str]:
    logs = json.load(log_file.open())
    project_name = logs["settings"]["cdm_source_name"]
    omop_es_timestamp = datetime.fromisoformat(logs["datetime"])
    project_name_slug = extract.copy_to_exports(dir_path, project_name, omop_es_timestamp)
    return omop_es_timestamp, project_name_slug
