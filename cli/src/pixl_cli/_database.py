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

"""Interaction with the PIXL database."""

from typing import cast

import pandas as pd
from core.db.models import Extract, Image
from sqlalchemy import URL, create_engine, not_, select
from sqlalchemy.orm import Session, sessionmaker

from pixl_cli._config import SERVICE_SETTINGS

connection_config = SERVICE_SETTINGS["postgres"]

url = URL.create(
    drivername="postgresql+psycopg2",
    username=connection_config["username"],
    password=connection_config["password"],
    host=connection_config["host"],
    port=connection_config["port"],
    database=connection_config["database"],
)

engine = create_engine(url)


def filter_exported_or_add_to_db(messages_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter exported images for multiple projects, and adds missing extract and images to database.

    :param messages: Initial messages to filter if they already exist
    :return DataFrame of messages that have not been exported
    """
    PixlSession = sessionmaker(engine)
    with PixlSession() as pixl_session, pixl_session.begin():
        messages_dfs = [
            _filter_exported_or_add_to_db_for_project(
                pixl_session, project_messages_df, project_slug
            )
            for project_slug, project_messages_df in messages_df.groupby("project_name")
        ]
    return pd.concat(messages_dfs)


def _filter_exported_or_add_to_db_for_project(
    session: Session, messages_df: pd.DataFrame, project_slug: str
) -> pd.DataFrame:
    """
    Filter exported images for this project, and adds missing extract and images to database.

    :param session: SQLAlchemy session
    :param messages: Initial messages to filter if they already exist
    :param project_slug: project slug to query on
    :return DataFrame of messages that have not been exported for this project
    """
    extract = session.query(Extract).filter(Extract.slug == project_slug).one_or_none()
    if extract:
        db_images_df = all_images_for_project(project_slug)
        missing_images_df = _filter_existing_images(messages_df, db_images_df)
        messages_df = _filter_exported_messages(messages_df, db_images_df)
    else:
        # We need to add the extract to the database and retrive it again so
        # we can access extract.extract_id (needed by session.bulk_save_objects(images))
        session.add(Extract(slug=project_slug))
        extract = session.query(Extract).filter(Extract.slug == project_slug).one_or_none()
        missing_images_df = messages_df

    _add_images_to_session(extract, missing_images_df, session)

    return messages_df


def _filter_existing_images(
    messages_df: pd.DataFrame,
    images_df: pd.DataFrame,
) -> pd.DataFrame:
    # DataFrame indices must batch when using df.isin (or df.index.isin)
    # So we re-index the DataFrames to match on the columns we want to compare
    messages_df_reindexed = messages_df.set_index(["accession_number", "mrn", "study_date"])
    images_df_reindexed = images_df.set_index(["accession_number", "mrn", "study_date"])
    keep_indices = ~messages_df_reindexed.index.isin(images_df_reindexed.index)
    return messages_df[keep_indices]


def _filter_exported_messages(
    messages_df: pd.DataFrame,
    images_df: pd.DataFrame,
) -> pd.DataFrame:
    merged = messages_df.merge(
        images_df,
        on=["accession_number", "mrn", "study_date"],
        how="left",
        validate="one_to_one",
        suffixes=(None, None),
    )
    keep_indices = merged["exported_at"].isna().to_numpy()
    return merged[keep_indices][messages_df.columns]


def _add_images_to_session(extract: Extract, images_df: pd.DataFrame, session: Session) -> None:
    images = []
    for _, row in images_df.iterrows():
        new_image = Image(
            accession_number=row["accession_number"],
            study_date=row["study_date"],
            mrn=row["mrn"],
            study_uid=row["study_uid"],
            extract=extract,
            extract_id=extract.extract_id,
            pseudo_patient_id=row["pseudo_patient_id"],
        )
        images.append(new_image)
    session.bulk_save_objects(images)


def all_images_for_project(project_slug: str) -> pd.DataFrame:
    """Given a project, get all images in the DB for that project."""
    PixlSession = sessionmaker(engine)

    query = (
        select(Image.accession_number, Image.study_date, Image.mrn, Image.exported_at)
        .join(Extract)
        .where(Extract.slug == project_slug)
    )
    with PixlSession() as session:
        return pd.read_sql(
            sql=query,
            con=session.bind,
        )


def exported_images_for_project(project_slug: str) -> list[Image]:
    """
    Given a project, get all images in the DB for that project
    that have not yet been exported.
    """
    PixlSession = sessionmaker(engine)
    with PixlSession() as session:
        return cast(
            list[Image],
            session.query(Image)
            .join(Extract)
            .filter(Extract.slug == project_slug)
            .filter(not_(Image.exported_at.is_(None)))
            .all(),
        )
