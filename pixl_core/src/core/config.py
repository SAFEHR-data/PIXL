"""Project-specific configuration for Pixl."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, validator


class _Project(BaseModel):
    name: str
    modalities: list[str]


class _TagOperations(BaseModel):
    base_profile: Path
    extension_profile: Optional[Path]

    @classmethod
    @validator("base_profile")
    def valid_base_path(cls, v: Path) -> Path:
        if not v.exists():
            msg = "Base profile should be an existing path"
            raise ValueError(msg)
        return v

    @classmethod
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

    @classmethod
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
