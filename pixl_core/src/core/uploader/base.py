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

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from core.uploader._secrets import AzureKeyVault

logger = logging.getLogger(__name__)


class Uploader(ABC):
    """Upload strategy interface."""

    @abstractmethod
    def __init__(self, project_slug: str, keyvault_alias: Optional[str]) -> None:
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

    @abstractmethod
    def upload_dicom_image(self, *args: Any, **kwargs: Any) -> None:
        """
        Abstract method to upload DICOM images. To be overwritten by child classes.
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
