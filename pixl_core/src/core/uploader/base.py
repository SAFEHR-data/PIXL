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
"""Functionality to upload files to a remote server."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from loguru import logger

from core.db.queries import have_already_exported_image, update_exported_at
from core.project_config.secrets import AzureKeyVault
from core.uploader._orthanc import get_tags_by_study

if TYPE_CHECKING:
    from core.uploader._orthanc import StudyTags


class Uploader(ABC):
    """Upload strategy interface."""

    @abstractmethod
    def __init__(self, project_slug: str, keyvault_alias: str | None) -> None:
        """
        Initialise the uploader for a specific project with the destination configuration and an
        AzureKeyvault instance. The keyvault is used to fetch the secrets required to connect to
        the remote destination.

        Child classes should implement the _set_config method to set the configuration for the
        upload strategy.

        :param :
        """
        self.project_slug = project_slug
        self.keyvault_alias = keyvault_alias
        self.keyvault = AzureKeyVault()
        self._set_config()

    @abstractmethod
    def _set_config(self) -> None:
        """Set the configuration for the uploader."""

    def upload_dicom_and_update_database(self, study_id: str) -> None:
        """
        Upload the DICOM data, updating the database with an export datetime.
        Child classes implement how to upload a dicom image, this is a template method
        that ensures that the database interaction is always implemented
        :param study_id: Orthanc Study ID
        :raise: if the image has already been exported
        """
        study_tags = self._get_tags_by_study(study_id)
        self.check_already_exported(study_tags.pseudo_anon_image_id)

        logger.info(
            "Starting {} upload of '{}' for {}",
            self.__class__.__name__.removesuffix("Uploader"),
            study_tags.pseudo_anon_image_id,
            self.project_slug,
        )
        self._upload_dicom_image(study_id, study_tags)
        logger.success(
            "Finished {} upload of '{}'",
            self.__class__.__name__.removesuffix("Uploader"),
            study_tags.pseudo_anon_image_id,
        )

        update_exported_at(study_tags.pseudo_anon_image_id, datetime.now(tz=UTC))

    @abstractmethod
    def _upload_dicom_image(
        self,
        study_id: str,
        study_tags: StudyTags,
    ) -> None:
        """
        Abstract method to upload DICOM images, should not be called directly.
        To be overwritten by child classes.
        If an upload strategy does not support DICOM images, this method should raise a
        NotImplementedError.
        """

    @abstractmethod
    def upload_parquet_files(self, *args: Any, **kwargs: Any) -> None:
        """
        Abstract method to upload parquet files. To be overwritten by child classes.
        If an upload strategy does not support parquet files, this method should raise a
        NotImplementedError.
        """

    @staticmethod
    def check_already_exported(pseudo_anon_image_id: str) -> None:
        """Check if the image has already been exported."""
        if have_already_exported_image(pseudo_anon_image_id):
            msg = "Image already exported"
            raise RuntimeError(msg)

    @staticmethod
    def _get_tags_by_study(study_id: str) -> StudyTags:
        """Helper method for getting tags by study ID, can be overriden for testing."""
        return get_tags_by_study(study_id)
