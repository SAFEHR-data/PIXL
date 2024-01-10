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

from core.database import Image
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker

from pixl_dcmd._config import cli_config

connection_config = cli_config["postgres"]

url = URL.create(
    drivername="postgresql+psycopg2",
    username=connection_config["username"],
    password=connection_config["password"],
    host=connection_config["host"],
    port=connection_config["port"],
    database=connection_config["database"],
)

engine = create_engine(url)


def insert_new_uid_into_db_entity(existing_image: Image, hashed_value: str) -> Image:
    PixlSession = sessionmaker(engine)
    with PixlSession() as pixl_session, pixl_session.begin():
        existing_image.hashed_identifier = hashed_value
        pixl_session.add(existing_image)

        updated_image = (
            pixl_session.query(Image)
            .filter(
                Image.accession_number == existing_image.accession_number,
                Image.mrn == existing_image.mrn,
                Image.hashed_identifier == hashed_value,
            )
            .one_or_none()
        )

        return updated_image


def query_db(mrn: str, accession_number: str) -> Image:
    PixlSession = sessionmaker(engine)
    with PixlSession() as pixl_session, pixl_session.begin():
        existing_image = (
            pixl_session.query(Image)
            .filter(
                Image.accession_number == accession_number,
                Image.mrn == mrn,
                Image.exported_at is None,
            )
            .one()
        )

        return existing_image
