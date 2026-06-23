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

"""Image operations for a project."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, field_validator

if TYPE_CHECKING:
    from core.project_config.pixl_config_model import PixlConfig


def load_image_operations(pixl_config: PixlConfig) -> ImageOperations:
    """
    Load image operations for a project.
    :param pixl_config: Project configuration
    """
    image_operation_files = pixl_config.image_operation_files

    if image_operation_files is None:
        return ImageOperations(deid_recipes=None)
    return ImageOperations(deid_recipes=image_operation_files.deid_recipes)


class ImageOperations(BaseModel):
    """
    Image operations for a project.
    Provides access to the image operation schemes for a project.

    :param project_config: Project configuration
    :param deid_recipes: deid recipes containing image alterations
    """

    deid_recipes: list[Path] | None

    @staticmethod
    def _load_recipe(image_operation_file: Path) -> Any:
        return image_operation_file.read_text()

    @field_validator("deid_recipes")
    @classmethod
    def _valid_recipes(cls, recipes: list[Path]) -> list[Path] | None:
        if recipes is None:
            return None
        if not isinstance(recipes, list):
            msg = "Recipes must be a list of Paths."
            raise TypeError(msg)
        for recipe in recipes:
            _check_recipe(cls._load_recipe(recipe))
        return recipes


def _check_recipe(recipe_text: str) -> None:
    """
    Check recipe file.

    Note: currently assumes recipe uses SequenceOfUltrasoundRegions tag.
    These checks could be expanded for custom image operation files (e.g. not deid) in future.
    """
    if "SequenceOfUltrasoundRegions" not in recipe_text:
        invalid_recipe_msg = "Recipe must contain SequenceOfUltrasoundRegions DICOM tag."
        raise ValueError(invalid_recipe_msg)
