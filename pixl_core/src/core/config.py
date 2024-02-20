"""Project-specific configuration for Pixl."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import yaml
from pydantic import BaseModel, validator

if TYPE_CHECKING:
    from typing_extensions import Any


class _Project(BaseModel):
    name: str
    modalities: list[str]


class _TagOperations(BaseModel):
    base_profile: Path
    extension_profile: Optional[Path]

    @validator("base_profile")
    def valid_base_path(cls, v: Path) -> Path:
        if not v.exists():
            msg = "Base profile should be an existing path"
            raise ValueError(msg)
        return v

    @validator("extension_profile")
    def valid_extenstion_path(cls, v: Path) -> Path:
        if isinstance(v, Path) & (not v.exists()):
            msg = "Extension profile should be an existing path"
            raise ValueError(msg)
        return v


class _DestinationEnum(str, Enum):
    """Defines the valid upload destinations."""

    none = "none"
    ftps = "ftps"
    azure = "azure"
    dicomweb = "dicomweb"


class _Destination(BaseModel):
    dicom: _DestinationEnum
    parquet: _DestinationEnum

    @validator("parquet")
    def valid_parquet_destination(cls, v: str) -> str:
        if v == "dicomweb":
            msg = "Parquet destination cannot be dicomweb"
            raise ValueError(msg)
        return v


class PixlConfig(BaseModel):
    """Project-specific configuration for Pixl."""

    project: _Project
    tag_operations: _TagOperations
    destination: _Destination


def load_config(filename: Path) -> Any:
    """
    Load configuration from a yaml file.
    :param filename: Path to the yaml file
    """
    yaml_data = yaml.safe_load(filename.read_text())
    return PixlConfig.parse_obj(yaml_data)
