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
from sqlalchemy import URL, create_engine, update
from sqlalchemy.orm import sessionmaker

from pixl_cli._config import cli_config

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


def insert_new_uid_into_db_entity(
    mrn: str, accession_number: str, new_uid: str
) -> None:
    PixlSession = sessionmaker(engine)
    with PixlSession() as pixl_session, pixl_session.begin():
        existing_image = (
            pixl_session.query(Image)
            .filter(
                Image.accession_number == accession_number,
                Image.mrn == mrn,
            )
            .one_or_none()
        )

        if existing_image:
            stmt = (
                update(Image)
                .where(Image.extract_id == existing_image.extract_id)
                .values(hashed_identifier=new_uid)
            )
            pixl_session.execute(stmt)


def query_db(mrn: str, accession_number: str) -> bool:
    PixlSession = sessionmaker(engine)
    with PixlSession() as pixl_session, pixl_session.begin():
        existing_image = (
            pixl_session.query(Image)
            .filter(
                Image.accession_number == accession_number,
                Image.mrn == mrn,
            )
            .one_or_none()
        )

        if existing_image.exported_at is not None:
            return True
        return False
