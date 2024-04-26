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
"""Processing of OMOP parquet files."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pandas as pd
import slugify

from core.project_config import load_project_config
from core.uploader import get_uploader

if TYPE_CHECKING:
    import datetime
    import pathlib


from loguru import logger


class ParquetExport:
    """Exporting Omop and Emap extracts to Parquet files."""

    def __init__(
        self, project_name_raw: str, extract_datetime: datetime.datetime, export_dir: pathlib.Path
    ) -> None:
        """
        :param project_name_raw: original name of the project (pre-sluggify)
        :param extract_datetime: datetime that the OMOP ES extract was run
        :param export_dir: Root directory to export files to. Don't forget that the CLI has a
                        different view of the filesystem than the docker containers do.
        """
        self.export_dir = export_dir
        self.project_slug, self.extract_time_slug = self._get_slugs(
            project_name_raw, extract_datetime
        )
        project_base = self.export_dir / self.project_slug

        self.current_extract_base = project_base / "all_extracts" / self.extract_time_slug
        self.public_output = self.current_extract_base / "omop" / "public"
        self.radiology_output = self.current_extract_base / "radiology"
        self.latest_symlink = project_base / "latest"

    @staticmethod
    def _get_slugs(project_name: str, extract_datetime: datetime.datetime) -> tuple[str, str]:
        """Convert project name and datetime to slugs for writing to filesystem."""
        project_slug = slugify.slugify(project_name)
        extract_time_slug = slugify.slugify(extract_datetime.isoformat())
        return project_slug, extract_time_slug

    def copy_to_exports(self, input_omop_dir: pathlib.Path) -> str:
        """
        Copy public omop directory as the latest extract for the project.
        Creates directories if they don't already exist.
        :param input_omop_dir: parent path for input omop data, with a "public" subdirectory
        :raises FileNotFoundError: if there is no public subdirectory in `omop_dir`
        :returns str: the project slug, so this can be registered for export to the DSH

        The final directory structure will look like this:
            exports
            └── <project_slug>
                ├── all_extracts
                │   └── <extract_datetime_slug>
                │       ├── omop
                │       │   └── public
                │       │       └── PROCEDURE_OCCURRENCE.parquet
                │       └── radiology
                │           └── radiology.parquet
                └── latest -> </symlink/to/latest/extract>
        """
        public_input = input_omop_dir / "public"

        logger.info("Copying public parquet files from {} to {}", public_input, self.public_output)

        # Make sure the base export direcotry exsists
        if not self.export_dir.exists():
            msg = f"Export directory {self.export_dir} does not exist"
            raise FileNotFoundError(msg)

        # Make directory for project exports
        ParquetExport._mkdir(self.public_output)

        # Copy extract files, overwriting if it exists
        shutil.copytree(public_input, self.public_output, dirs_exist_ok=True)

        # Symlink this extract to the latest directory
        self.latest_symlink.unlink(missing_ok=True)
        self.latest_symlink.symlink_to(self.current_extract_base, target_is_directory=True)
        return self.project_slug

    def export_radiology_linker(self, linker_data: pd.DataFrame):
        linker_data.to_parquet(self.radiology_output / "IMAGE_LINKER.parquet")

    @staticmethod
    def _mkdir(directory: pathlib.Path) -> pathlib.Path:
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def upload(self) -> None:
        """Upload the latest extract to the DSH."""
        project_config = load_project_config(self.project_slug)
        destination = project_config.destination.parquet

        if destination == "none":
            msg = (
                f"Destination for parquet files for project {self.project_slug} is 'none'."
                "Skipping upload."
            )
            logger.info(msg)

        else:
            uploader = get_uploader(
                self.project_slug, destination, project_config.project.azure_kv_alias
            )

            msg = f"Uploading parquet files for project {self.project_slug} via '{destination}'"
            logger.info(msg)
            uploader.upload_parquet_files(self)
