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

import logging
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from decouple import config
from pydantic import BaseModel, field_validator

PROJECT_CONFIGS_DIR = Path(config("PROJECT_CONFIGS_DIR"))

logger = logging.getLogger(__name__)


def load_project_config(project_slug: str) -> Any:
    """
    Load configuration for a project based on its slug.
    Project needs to have a corresponding yaml file in the /config directory.
    """
    configpath = PROJECT_CONFIGS_DIR / f"{project_slug}.yaml"
    logger.warning(f"Loading config for {project_slug} from {configpath}")  # noqa: G004
    if not configpath.exists():
        raise FileNotFoundError(f"No config for {project_slug}. Please submit PR and redeploy.")  # noqa: EM102, TRY003
    return _load_project_config(configpath)


def _load_project_config(filename: Path) -> Any:
    """
    Load configuration from a yaml file.
    :param filename: Path to the yaml file
    """
    yaml_data = yaml.safe_load(filename.read_text())
    return PixlConfig.model_validate(yaml_data)


class _Project(BaseModel):
    name: str
    modalities: list[str]


class _DestinationEnum(str, Enum):
    """Defines the valid upload destinations."""

    none = "none"
    ftps = "ftps"
    azure = "azure"
    dicomweb = "dicomweb"


class _Destination(BaseModel):
    dicom: _DestinationEnum
    parquet: _DestinationEnum

    @field_validator("parquet")
    def valid_parquet_destination(cls, v: str) -> str:
        if v == "dicomweb":
            msg = "Parquet destination cannot be dicomweb"
            raise ValueError(msg)
        return v


class PixlConfig(BaseModel):
    """Project-specific configuration for Pixl."""

    project: _Project
    tag_operation_files: list[Path]
    destination: _Destination

    @field_validator("tag_operation_files", mode="before")
    def _valid_tag_operations(cls, tag_ops_files: list[str]) -> list[Path]:
        if not tag_ops_files or len(tag_ops_files) == 0:
            msg = "There should be at least 1 tag operations file"
            raise ValueError(msg)

        # Pydantic will automatically check if the file exists
        return [
            PROJECT_CONFIGS_DIR / "tag-operations" / tag_ops_file for tag_ops_file in tag_ops_files
        ]
