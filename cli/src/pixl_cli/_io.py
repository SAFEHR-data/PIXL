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
"""Reading and writing files from PIXL CLI."""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum, auto
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from core.exports import ParquetExport
from loguru import logger

from pixl_cli._config import HOST_EXPORT_ROOT_DIR

if TYPE_CHECKING:
    from pathlib import Path

    from core.db.models import Image


def project_info(resources_path: Path) -> tuple[str, datetime]:
    """
    Get the project name and extract timestamp from the extract summary log file.
    :param resources_path: path to the input resources
    """
    log_file = resources_path / "extract_summary.json"
    logs = json.load(log_file.open())
    project_name = logs["settings"]["cdm_source_name"]
    extract_generated_timestamp = datetime.fromisoformat(logs["datetime"])
    return project_name, extract_generated_timestamp


def copy_parquet_return_logfile_fields(resources_path: Path) -> tuple[str, datetime]:
    """Copy public parquet file to extracts directory, and return fields from logfile"""
    project_name_raw, extract_generated_timestamp = project_info(resources_path)
    extract = ParquetExport(project_name_raw, extract_generated_timestamp, HOST_EXPORT_ROOT_DIR)
    project_name_slug = extract.copy_to_exports(resources_path)
    return project_name_slug, extract_generated_timestamp


def read_patient_info(resources_path: Path) -> pd.DataFrame:
    """
    Read patient information from a CSV file or parquet files within directory structure.
    :param resources_path: Path for CSV file or parquet directory containing private and public
    :return: DataFrame with patient information
    """
    if resources_path.is_file() and resources_path.suffix == ".csv":
        messages_df = _load_csv(resources_path)
    else:
        messages_df = _load_parquet(resources_path)

    # Tidy up dataframe in case of whitespace or no way to identify images
    unique_columns = ["project_name", "mrn", "accession_number", "study_uid"]
    filtered_df = messages_df.dropna(subset=["accession_number", "study_uid"], how="all")
    for column in unique_columns:
        filtered_df[column] = filtered_df[column].str.strip()
    filtered_df = filtered_df[
        ~(filtered_df["accession_number"].eq("") & filtered_df["study_uid"].eq(""))
    ]

    filtered_df = filtered_df.sort_values(by=["project_name", "study_date"])
    filtered_df = filtered_df.drop_duplicates(subset=unique_columns)

    if len(filtered_df) == 0:
        msg = f"Failed to find any messages in {resources_path}"
        raise ValueError(msg)

    logger.info("Created {} messages from {}", len(filtered_df), resources_path)

    return filtered_df


def _load_csv(filepath: Path) -> pd.DataFrame:
    """
    Reads patient information from CSV and transforms that into messages.
    :param filepath: Path for CSV file to be read
    """
    # First line is column names
    messages_df = pd.read_csv(filepath, header=0, dtype=str)
    messages_df = _map_columns(messages_df, MAP_CSV_TO_MESSAGE_KEYS)
    _raise_if_column_names_not_found(messages_df, [col.name for col in DF_COLUMNS])
    messages_df["series_uid"] = messages_df.get("series_uid", "").replace(np.nan, "").str.strip()
    messages_df["pseudo_patient_id"] = messages_df["pseudo_patient_id"].replace(np.nan, None)

    # Parse non string columns
    messages_df["procedure_occurrence_id"] = messages_df["procedure_occurrence_id"].astype(int)
    messages_df["study_date"] = pd.to_datetime(
        messages_df["study_date"], format="%Y-%m-%d", errors="raise"
    ).dt.date
    messages_df["extract_generated_timestamp"] = pd.to_datetime(
        messages_df["extract_generated_timestamp"],
        format="%Y-%m-%dT%H:%M:%SZ",
        errors="raise",
        utc=True,
    )

    return messages_df


def _load_parquet(
    dir_path: Path,
) -> pd.DataFrame:
    """
    Reads patient information from parquet files within directory structure
    and transforms that into a DataFrame

    :param dir_path: Path for parquet directory containing private and public
    """
    public_dir = dir_path / "public"
    private_dir = dir_path / "private"

    messages_df = _check_and_parse_parquet(private_dir, public_dir)
    messages_df = _map_columns(messages_df, MAP_PARQUET_TO_MESSAGE_KEYS)

    project_name, extract_generated_timestamp = copy_parquet_return_logfile_fields(dir_path)
    messages_df["project_name"] = project_name
    messages_df["extract_generated_timestamp"] = extract_generated_timestamp
    messages_df["pseudo_patient_id"] = None
    messages_df["series_uid"] = ""

    return messages_df


def _check_and_parse_parquet(private_dir: Path, public_dir: Path) -> pd.DataFrame:
    for d in [public_dir, private_dir]:
        if not d.is_dir():
            err_str = f"{d} must exist and be a directory"
            raise NotADirectoryError(err_str)

    # MRN in people.PrimaryMrn:
    people = pd.read_parquet(private_dir / "PERSON_LINKS.parquet")
    # accession number in accessions.AccessionNumber
    accessions = pd.read_parquet(private_dir / "PROCEDURE_OCCURRENCE_LINKS.parquet")
    # study_date is in procedure.procedure_date
    procedure = pd.read_parquet(public_dir / "PROCEDURE_OCCURRENCE.parquet")

    # joining data together
    people_procedures = people.merge(procedure, on="person_id")
    people_procedures_accessions = people_procedures.merge(accessions, on="procedure_occurrence_id")

    # Filter out any rows where accession number is NA or an empty string
    return people_procedures_accessions[
        ~people_procedures_accessions["AccessionNumber"].isna()
        & (people_procedures_accessions["AccessionNumber"] != "")
    ]


class DF_COLUMNS(StrEnum):  # noqa: N801
    procedure_occurrence_id = auto()
    mrn = auto()
    accession_number = auto()
    project_name = auto()
    extract_generated_timestamp = auto()
    study_date = auto()
    study_uid = auto()
    pseudo_patient_id = auto()


MAP_CSV_TO_MESSAGE_KEYS = {
    "procedure_id": "procedure_occurrence_id",
    "participant_id": "pseudo_patient_id",
}

MAP_PARQUET_TO_MESSAGE_KEYS = {
    "PrimaryMrn": "mrn",
    "AccessionNumber": "accession_number",
    "procedure_date": "study_date",
    "StudyUid_X": "study_uid",
}


def _map_columns(input_df: pd.DataFrame, columns: dict) -> pd.DataFrame:
    _raise_if_column_names_not_found(input_df, list(columns.keys()))
    return input_df.rename(columns, axis=1)


def _raise_if_column_names_not_found(
    cohort_data: pd.DataFrame, expected_col_names: list[str]
) -> None:
    logger.debug(
        "Checking merged parquet files. Expecting columns to include {}", expected_col_names
    )
    for col in expected_col_names:
        if col not in list(cohort_data.columns):
            msg = (
                f"Export specification files are expected to have at least {expected_col_names} as "
                f"column names"
            )
            raise ValueError(msg)


def make_radiology_linker_table(parquet_dir: Path, images: list[Image]) -> pd.DataFrame:
    """
    Make a table linking the OMOP procedure_occurrence_id to the pseudo image/study ID.
    :param parquet_dir: location of OMOP extract
                        (this gives us: procedure_occurrence_id <-> mrn+accession mapping)
    :param images: the images already processed by PIXL, from the DB
                        (this gives us: mrn+accession <-> pseudo_study_uid)
    """
    public_dir = parquet_dir / "public"
    private_dir = parquet_dir / "private"
    people_procedures_accessions = _map_columns(
        _check_and_parse_parquet(private_dir, public_dir),
        MAP_PARQUET_TO_MESSAGE_KEYS,
    )

    images_df = pd.DataFrame.from_records([vars(im) for im in images])
    merged = people_procedures_accessions.merge(images_df, on=("mrn", "accession_number"))
    return merged[["procedure_occurrence_id", "pseudo_study_uid"]]
