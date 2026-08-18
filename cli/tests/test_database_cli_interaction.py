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

"""Test database interaction methods for the cli."""

from core.db.models import Extract, Image
from pandas.testing import assert_frame_equal
from pixl_cli._database import exported_images_for_project, filter_exported_or_add_to_db


def test_project_doesnt_exist(example_messages_df, db_session):
    """If project doesn't exist, no filtering and then project & messages saved to database"""
    output = filter_exported_or_add_to_db(example_messages_df)
    assert_frame_equal(output, example_messages_df)
    extract = db_session.query(Extract).one()
    images = db_session.query(Image).filter(Image.extract == extract).all()
    assert len(images) == len(example_messages_df)


def test_first_image_exported(example_messages_df, rows_in_session):
    """
    GIVEN 3 messages, where one has been exported, the second has been saved to db but not exported
    WHEN the messages are filtered
    THEN the first message that has an exported_at value should not be in the filtered list
        and all images should be saved to the database
    """
    output = filter_exported_or_add_to_db(example_messages_df)
    assert len(output) == len(example_messages_df) - 1
    assert "123" not in output.accession_number.to_numpy()
    extract = rows_in_session.query(Extract).one()
    images = rows_in_session.query(Image).filter(Image.extract == extract).all()
    assert len(images) == len(example_messages_df)


def test_new_extract_with_overlapping_images(example_messages_df, rows_in_session):
    """
    GIVEN messages from a new extract, two have been saved to the database with another extract
    WHEN the messages are filtered
    THEN all messages should be returned and all new images should be added
    """
    new_project_name = "new-project"
    example_messages_df["project_name"] = new_project_name

    output = filter_exported_or_add_to_db(example_messages_df)

    # none filtered out
    assert len(output) == len(example_messages_df)
    # all new batch of images saved
    extract = rows_in_session.query(Extract).filter(Extract.slug == new_project_name).one()
    images = rows_in_session.query(Image).filter(Image.extract == extract).all()
    assert len(images) == len(example_messages_df)
    # other extract and images still in database
    assert len(rows_in_session.query(Extract).all()) > 1
    assert len(rows_in_session.query(Image).all()) > len(example_messages_df)


def test_processed_images_for_project(rows_in_session):
    """
    GIVEN a project with 3 images in the database, only one of which is exported
    WHEN the processed_images_for_project function is called
    THEN only the exported images are returned
    """
    processed = exported_images_for_project("i-am-a-project")
    assert len(processed) == 1
    assert processed[0].accession_number == "123"


def test_reimport_of_previously_skipped_image(example_messages_df, rows_in_session):
    """
    GIVEN an image that previously had all instances skipped during anonymisation and has
        skip_reasons recorded against it, but has not been exported
    WHEN the same messages are re-imported (filtered again for the same project)
    THEN no duplicate row should be added for that image (row-level filtering)
        and the image should not be returned for reprocessing, as it previously failed
        anonymisation (export-status filtering), with its recorded skip_reasons left untouched
    """
    extract = rows_in_session.query(Extract).one()
    previously_skipped_image = (
        rows_in_session.query(Image)
        .filter(Image.extract == extract, Image.accession_number == "234")
        .one()
    )
    skip_reasons = {"DICOM instance discarded as series has too few instances": 3}
    previously_skipped_image.skip_reasons = skip_reasons
    rows_in_session.commit()

    output = filter_exported_or_add_to_db(example_messages_df)

    # Row-level: re-importing must not create a duplicate row for the existing image
    images = rows_in_session.query(Image).filter(Image.extract == extract).all()
    assert len(images) == len(example_messages_df)

    # Filtering-level: failed anonymisation images are not queued again,
    # nor are already-exported images
    accession_numbers = output.accession_number.to_numpy()
    assert "234" not in accession_numbers
    assert "123" not in accession_numbers
    assert "345" in accession_numbers
    assert len(output) == 1

    # The recorded skip reasons must survive the re-import untouched
    reloaded_image = (
        rows_in_session.query(Image)
        .filter(Image.extract == extract, Image.accession_number == "234")
        .one()
    )
    assert reloaded_image.skip_reasons == skip_reasons
