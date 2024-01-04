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

"""Create PIXL tables"""
import os

from core.database import Base
from sqlalchemy import URL, create_engine
from sqlalchemy.sql.ddl import CreateSchema

url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    database=os.environ["POSTGRES_DB"],
)

engine = create_engine(url, echo=True, echo_pool="debug")

with engine.connect() as connection:
    connection.execute(CreateSchema("pixl", if_not_exists=True))
    connection.commit()

Base.metadata.create_all(engine)
