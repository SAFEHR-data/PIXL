"""Create PIXL tables"""
import os

from core.database import Base
from sqlalchemy import URL, create_engine

url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    database=os.environ["POSTGRES_DB"],
)

engine = create_engine(url, echo=True, echo_pool="debug")
Base.metadata.create_all(engine)
