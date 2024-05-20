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
"""Test base uploader functionality."""

import pytest
import sqlalchemy
from core.db.models import Image
from core.uploader.base import Uploader
from loguru import logger
from sqlalchemy.orm import sessionmaker


class DumbUploader(Uploader):
    """
    Mock Uploader that has no interation with orthanc anon and doesn't upload anything..

    Allows testing of the database interaction at the top level call to uploader.
    """

    def __init__(self, pseudo_study_uid) -> None:
        """Initialise the mock uploader with hardcoded values for FTPS config."""
        self.pseudo_study_uid = pseudo_study_uid

    def _get_tags_by_study(self, study_id: str) -> tuple[str, str]:
        logger.info("Mocked getting tags for: {} to return {}", study_id, self.pseudo_study_uid)
        return self.pseudo_study_uid, "project_slug"

    def _upload_dicom_image(
        self, study_id: str, pseudo_anon_image_id: str, project_slug: str
    ) -> None:
        logger.info(
            "Mocked uploader with no upload functionality for {}, {}, {}",
            study_id,
            pseudo_anon_image_id,
            project_slug,
        )

    def _set_config(self) -> None:
        """Required from ABC."""
        raise NotImplementedError

    def upload_parquet_files(self) -> None:
        """Required from ABC."""
        raise NotImplementedError


def test_export_date_updated(db_engine, not_yet_exported_dicom_image) -> None:
    """
    GIVEN that a study hasn't been exported yet, orthanc anon and upload to ftps has been mocked out
    WHEN the study is exported by the top level upload dicom and update db method
    THEN the file will be uploaded

    Each child class implementation tests the upload functionality
    """
    # ARRANGE
    study_id = "test-study-id"
    uploader = DumbUploader(not_yet_exported_dicom_image.pseudo_study_uid)

    # ACT
    uploader.upload_dicom_and_update_database(study_id)

    # ASSERT
    InMemorySession = sessionmaker(db_engine)
    with InMemorySession() as session:
        output = (
            session.query(Image).filter(Image.pseudo_study_uid == uploader.pseudo_study_uid).one()
        )
    assert output.exported_at is not None


def test_unknown_study_raises(rows_in_session) -> None:
    """
    GIVEN that a study isn't in the database
    WHEN dicom trys to be upload
    THEN an exception is raised
    """
    study_id = "test-study-id"
    uploader = DumbUploader("not in db")

    with pytest.raises(sqlalchemy.exc.NoResultFound):
        uploader.upload_dicom_and_update_database(study_id)


def test_study_already_exported_raises(already_exported_dicom_image) -> None:
    """
    GIVEN that a study has already been exported
    WHEN dicom trys to be upload
    THEN an exception is raised
    """
    study_id = "test-study-id"
    uploader = DumbUploader(already_exported_dicom_image.pseudo_study_uid)

    with pytest.raises(RuntimeError, match="Image already exported"):
        uploader.upload_dicom_and_update_database(study_id)
