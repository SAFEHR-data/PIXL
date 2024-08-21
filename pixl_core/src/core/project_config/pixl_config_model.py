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

"""Project-specific configuration for Pixl."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml
from decouple import Config, RepositoryEmpty, RepositoryEnv
from loguru import logger
from pydantic import BaseModel, field_validator

from core.exceptions import PixlDiscardError

# Make sure local .env file is loaded if it exists
env_file = Path.cwd() / ".env"
config = Config(RepositoryEnv(env_file)) if env_file.exists() else Config(RepositoryEmpty())


def load_project_config(project_slug: str) -> PixlConfig | Any:
    """
    Load configuration for a project based on its slug.
    Project needs to have a corresponding yaml file in the `$PROJECT_CONFIGS_DIR` directory.
    """
    configpath = Path(config("PROJECT_CONFIGS_DIR")) / f"{project_slug}.yaml"
    try:
        return load_config_and_validate(configpath)
    except FileNotFoundError as error:
        msg = f"No config for {project_slug}. Please submit PR and redeploy."
        raise PixlDiscardError(msg) from error


def load_config_and_validate(filename: Path) -> PixlConfig | Any:
    """
    Load configuration from a yaml file.
    :param filename: Path to the yaml file
    """
    logger.debug("Loading config from {}", filename)
    yaml_data = yaml.safe_load(filename.read_text())
    return PixlConfig.model_validate(yaml_data)


class _Project(BaseModel):
    name: str
    azure_kv_alias: Optional[str] = None
    modalities: list[str]


class TagOperationFiles(BaseModel):
    """Tag operations files for a project. At least a base file is required."""

    base: list[Path]
    manufacturer_overrides: Optional[list[Path]]

    @field_validator("base")
    @classmethod
    def _valid_tag_operations(cls, tag_ops_files: list[str]) -> list[Path]:
        if not tag_ops_files or len(tag_ops_files) == 0:
            msg = "There should be at least 1 tag operations file"
            raise ValueError(msg)

        # Pydantic does not appear to automatically check if the file exists
        files = [
            Path(config("PROJECT_CONFIGS_DIR")) / "tag-operations" / tag_ops_file
            for tag_ops_file in tag_ops_files
        ]
        for f in files:
            if not f.exists():
                # For pydantic, you must raise a ValueError (or AssertionError)
                raise ValueError from FileNotFoundError(f)
        return files

    @field_validator("manufacturer_overrides")
    @classmethod
    def _valid_manufacturer_overrides(cls, tag_files: list[str]) -> Optional[list[Path]]:
        if not tag_files:
            return None

        tag_file_paths = []
        for tag_file in tag_files:
            tag_file_path = (
                Path(config("PROJECT_CONFIGS_DIR"))
                / "tag-operations"
                / "manufacturer-overrides"
                / tag_file
            )
            # Pydantic does not appear to automatically check if the file exists
            if not tag_file_path.exists():
                # For pydantic, you must raise a ValueError (or AssertionError)
                raise ValueError from FileNotFoundError(tag_file_path)
            tag_file_paths.append(tag_file_path)
        return tag_file_paths


class _DestinationEnum(str, Enum):
    """Defines the valid upload destinations."""

    none = "none"
    ftps = "ftps"
    dicomweb = "dicomweb"


class _Destination(BaseModel):
    dicom: _DestinationEnum
    parquet: _DestinationEnum

    @field_validator("parquet")
    @classmethod
    def valid_parquet_destination(cls, v: str) -> str:
        if v == "dicomweb":
            msg = "Parquet destination cannot be dicomweb"
            raise ValueError(msg)
        return v


class PixlConfig(BaseModel):
    """Project-specific configuration for Pixl."""

    project: _Project
    series_filters: Optional[list[str]] = None
    tag_operation_files: TagOperationFiles
    destination: _Destination

    def is_series_excluded(self, series_description: str) -> bool:
        """
        Return whether this config excludes the series with the given description
        :param series_description: the series description to test
        :returns: True if it should be excluded, False if not
        """
        if self.series_filters is None or series_description is None:
            return False
        # Do a simple case-insensitive substring check - this data is ultimately typed by a human,
        # and different image sources may have different conventions for case conversion.
        return any(
            series_description.upper().find(filt.upper()) != -1 for filt in self.series_filters
        )
