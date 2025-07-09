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
from loguru import logger
from sqlalchemy.orm import sessionmaker

from core.db.models import Image
from core.uploader import DicomWebUploader, FTPSUploader, XNATUploader, get_uploader
from core.uploader._orthanc import StudyTags
from core.uploader.base import Uploader


class DumbUploader(Uploader):
    """
    Mock Uploader that has no interation with orthanc anon and doesn't upload anything..

    Allows testing of the database interaction at the top level call to uploader.
    """

    def __init__(self, pseudo_study_uid) -> None:
        """Initialise the mock uploader with hardcoded values for FTPS config."""
        self.project_slug = "project_slug"
        self.pseudo_study_uid = pseudo_study_uid

    def _get_tags_by_study(self, study_id: str) -> StudyTags:
        logger.info("Mocked getting tags for: {} to return {}", study_id, self.pseudo_study_uid)
        return StudyTags(self.pseudo_study_uid, "patient-id")

    def _upload_dicom_image(
        self,
        study_id: str,
        study_tags: StudyTags,
    ) -> None:
        logger.info(
            "Mocked uploader with no upload functionality for {}, {}, {}",
            study_id,
            study_tags.pseudo_anon_image_id,
            self.project_slug,
            study_tags.patient_id,
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


@pytest.mark.parametrize(
    ("project_slug", "expected_uploader_class"),
    [
        ("test-extract-uclh-omop-cdm", FTPSUploader),
        ("test-extract-uclh-omop-cdm-dicomweb", DicomWebUploader),
        ("test-extract-uclh-omop-cdm-xnat", XNATUploader),
    ],
)
def test_get_uploader(project_slug, expected_uploader_class, monkeypatch) -> None:
    """Test the correct uploader class is returned."""
    with monkeypatch.context() as m:
        # Mock the __init__ method so that we don't attempt to connect to AzureKeyVault.
        # Otherwise AzureKeyVault._check_envvars will raise an exception for undefined
        # environment variables.
        m.setattr(
            "core.uploader.base.Uploader.__init__",
            lambda self, project_slug, keyvault_alias: None,  # noqa: ARG005
        )

        uploader = get_uploader(project_slug)
        assert isinstance(uploader, expected_uploader_class)
