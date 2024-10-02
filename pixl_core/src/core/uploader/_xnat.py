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

"""Uploader subclass for XNAT."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, BinaryIO, Optional

import xnat

from core.uploader.base import Uploader

from ._orthanc import get_study_zip_archive

if TYPE_CHECKING:
    from xnat.core import XNATBaseObject

    from core.exports import ParquetExport
    from core.uploader._orthanc import StudyTags


class XNATUploader(Uploader):
    """Upload strategy for an XNAT server."""

    def __init__(self, project_slug: str, keyvault_alias: Optional[str]) -> None:
        """Create instance of parent class"""
        super().__init__(project_slug, keyvault_alias)

    def _set_config(self) -> None:
        """
        Configure XNATUploader.

        "XNAT_DESTINATION":
        - if "/archive", will send data straight to the archive
        - if "/prearchive", will send data to the prearchive for manual review before archiving

        "XNAT_OVERWRITE":
          - if 'none', will error if the session already exists.
          - if 'append', will append the data to an existing session or create a new one if it
            doesn't exist.
            If there is a conflict with existing series, an error will be raised.
          - if 'delete', will append the data to an existing session or create a new one if it
            doesn't exist.
            If there is a conflict with existing series, the existing series will be overwritten.
        """
        # Use the Azure KV alias as prefix if it exists, otherwise use the project name
        az_prefix = self.keyvault_alias
        az_prefix = az_prefix if az_prefix else self.project_slug

        self.host = self.keyvault.fetch_secret(f"{az_prefix}--xnat--host")
        self.user = self.keyvault.fetch_secret(f"{az_prefix}--xnat--username")
        self.password = self.keyvault.fetch_secret(f"{az_prefix}--xnat--password")
        self.port = int(self.keyvault.fetch_secret(f"{az_prefix}--xnat--port"))
        self.url = f"https://{self.host}:{self.port}"
        self.destination = os.environ["XNAT_DESTINATION"]
        self.overwrite = os.environ["XNAT_OVERWRITE"]

    def _upload_dicom_image(
        self,
        study_id: str,
        study_tags: StudyTags,
    ) -> None:
        """Upload a DICOM image to the XNAT instance."""
        zip_content = get_study_zip_archive(study_id)
        self.upload_to_xnat(zip_content, study_tags)

    def upload_to_xnat(
        self,
        zip_content: BinaryIO,
        study_tags: StudyTags,
    ) -> XNATBaseObject:
        with xnat.connect(
            server=self.url,
            user=self.user,
            password=self.password,
        ) as session:
            session.services.import_(
                data=zip_content,
                overwrite=self.overwrite,
                destination=self.destination,
                project=study_tags.project_slug,
                subject=study_tags.patient_id,
                experiment=study_tags.pseudo_anon_image_id,
                content_type="application/zip",
                import_handler="DICOM-zip",
            )

    def upload_parquet_files(self, parquet_export: ParquetExport) -> None:  # noqa: ARG002
        msg = "XNATUploader does not support parquet files"
        raise NotImplementedError(msg)
