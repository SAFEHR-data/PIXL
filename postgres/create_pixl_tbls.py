"""Create PIXL tables"""
import os

from core.database import Base
from sqlalchemy import create_engine

user = os.environ["POSTGRES_USER"]
password = os.environ["POSTGRES_PASSWORD"]
DB = os.environ["POSTGRES_DB"]

conn = f"postgresql+psycopg2://{user}:{password}@/{DB}"
engine = create_engine(conn, echo=True, echo_pool="debug")
Base.metadata.create_all(engine)
