"""Interaction with the PIXL database."""
from core.database import Image
from sqlalchemy import URL, create_engine, select

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


def _number_of_images() -> int:
    """
    Dummy function to ensure that tests can be run
    will remove once we have real code to test.
    """
    query = select(Image)
    with engine.connect() as conn:
        output = conn.execute(query)
    return len([x.image_id for x in output])
