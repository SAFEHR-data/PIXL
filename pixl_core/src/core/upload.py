"""Functionality to upload files to an endpoint."""

import ftplib
import logging
import os
from datetime import datetime
from ftplib import FTP_TLS
from pathlib import Path
from typing import BinaryIO

from dateutil.tz import UTC

from core._database import get_project_slug_from_db, update_exported_at_and_save

logger = logging.getLogger(__name__)


# Make a DSHUploader class that takes a project slug and study pseudonymised id?


def upload_dicom_image(local_file_path: Path, pseudo_anon_id: str) -> str:
    """Top level way to upload an image."""
    # Create the remote directory if it doesn't exist
    # TODO: rename destination to {project-slug}/{study-pseduonymised-id}.zip
    remote_directory = get_project_slug_from_db(pseudo_anon_id)

    # Store the file using a binary handler
    with local_file_path.open("rb") as file_content:
        output_path = upload_content(
            # wrong directory name, can get that from the image at least
            file_content,
            remote_dir=remote_directory.hashed_identifier,
            remote_file=f"{remote_directory.hashed_identifier}.zip",
        )

    update_exported_at_and_save(datetime.now(tz=UTC))
    return output_path


def upload_content(content: BinaryIO, *, remote_dir: str, remote_file: str) -> str:
    """Upload local file to directory in ftp server."""
    ftp = _connect_to_ftp()

    _create_and_set_as_cwd(ftp, remote_dir)

    # Store the file using a binary handler
    command = f"STOR {remote_file}"
    logger.debug("Running %s", command)
    ftp.storbinary(command, content)

    # Close the FTP connection
    ftp.quit()
    logger.debug("Finished uploading!")
    return f"{remote_dir}/{remote_file}"


def _connect_to_ftp() -> FTP_TLS:
    # Set your FTP server details
    ftp_host = os.environ["FTP_HOST"]
    ftp_port = os.environ["FTP_PORT"]  # FTPS usually uses port 21
    ftp_user = os.environ["FTP_USER_NAME"]
    ftp_password = os.environ["FTP_USER_PASS"]

    # Connect to the server and login
    ftp = FTP_TLS()  # noqa: S321, we're required to use FTP_TLS
    ftp.connect(ftp_host, int(ftp_port))
    ftp.login(ftp_user, ftp_password)
    return ftp


def _create_and_set_as_cwd(ftp: FTP_TLS, project_dir: str) -> None:
    try:
        ftp.cwd(project_dir)
        logger.info("'%s' exists on remote ftp, so moving into it", project_dir)
    except ftplib.error_perm:
        logger.info("creating '%s' on remote ftp and moving into it", project_dir)
        # Directory doesn't exist, so create it
        ftp.mkd(project_dir)
        ftp.cwd(project_dir)
