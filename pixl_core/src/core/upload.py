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
"""Functionality to upload files to an endpoint."""

from __future__ import annotations

import ftplib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

if TYPE_CHECKING:
    from core.exports import ParquetExport


from core._upload_ftps import (
    _connect_to_ftp,
    _create_and_set_as_cwd,
    _create_and_set_as_cwd_multi_path,
)
from core.db.queries import get_project_slug_from_hashid, update_exported_at

logger = logging.getLogger(__name__)


def upload_dicom_image(zip_content: BinaryIO, pseudo_anon_id: str) -> None:
    """Top level way to upload an image."""
    logger.info("Starting FTPS upload of '%s'", pseudo_anon_id)

    # rename destination to {project-slug}/{study-pseduonymised-id}.zip
    remote_directory = get_project_slug_from_hashid(pseudo_anon_id)

    # Create the remote directory if it doesn't exist
    ftp = _connect_to_ftp()
    _create_and_set_as_cwd(ftp, remote_directory)
    command = f"STOR {pseudo_anon_id}.zip"
    logger.debug("Running %s", command)

    # Store the file using a binary handler
    try:
        ftp.storbinary(command, zip_content)
    except ftplib.all_errors as ftp_error:
        ftp.quit()
        error_msg = "Failed to run STOR command '%s': '%s'"
        raise ConnectionError(error_msg, command, ftp_error) from ftp_error

    # Close the FTP connection
    ftp.quit()

    update_exported_at(pseudo_anon_id, datetime.now(tz=timezone.utc))
    logger.info("Finished FTPS upload of '%s'", pseudo_anon_id)


def upload_parquet_files(parquet_export: ParquetExport) -> None:
    """
    Upload parquet to FTPS under <project name>/<extract datetime>/parquet.
    :param parquet_export: instance of the ParquetExport class
    The final directory structure will look like this:
    <project-slug>
    ├── <extract_datetime_slug>
    │   └── parquet
    │       ├── omop
    │       │   └── public
    │       │       └── PROCEDURE_OCCURRENCE.parquet
    │       └── radiology
    │           └── radiology.parquet
    ├── <pseudonymised_ID_DICOM_dataset_1>.zip
    └── <pseudonymised_ID_DICOM_dataset_2>.zip
    ...
    """
    logger.info("Starting FTPS upload of files for '%s'", parquet_export.project_slug)

    source_root_dir = parquet_export.current_extract_base
    # Create the remote directory if it doesn't exist
    ftp = _connect_to_ftp()
    _create_and_set_as_cwd(ftp, parquet_export.project_slug)
    _create_and_set_as_cwd(ftp, parquet_export.extract_time_slug)
    _create_and_set_as_cwd(ftp, "parquet")

    # get the upload root directory before we do anything as we'll need
    # to return to it (will it always be absolute?)
    upload_root_dir = Path(ftp.pwd())
    if not upload_root_dir.is_absolute():
        logger.error("server remote path is not absolute, what are we going to do?")

    # absolute paths of the source
    source_files = [x for x in source_root_dir.rglob("*.parquet") if x.is_file()]
    if not source_files:
        msg = f"No files found in {source_root_dir}"
        raise FileNotFoundError(msg)

    # throw exception if empty dir
    for source_path in source_files:
        _create_and_set_as_cwd(ftp, str(upload_root_dir))
        source_rel_path = source_path.relative_to(source_root_dir)
        source_rel_dir = source_rel_path.parent
        source_filename_only = source_rel_path.relative_to(source_rel_dir)
        _create_and_set_as_cwd_multi_path(ftp, source_rel_dir)
        with source_path.open("rb") as handle:
            command = f"STOR {source_filename_only}"

            # Store the file using a binary handler
            ftp.storbinary(command, handle)

    # Close the FTP connection
    ftp.quit()
    logger.info("Finished FTPS upload of files for '%s'", parquet_export.project_slug)
