"""Interaction with the PIXL database."""
from core.database import Image
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

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


def _number_of_images(session: Session = None) -> int:
    """
    Dummy function to ensure that tests can be run
    will remove once we have real code to test.
    """
    active_session = session or Session(engine)
    output = active_session.query(Image).where(Image.image_id is not None)
    return len([x.image_id for x in output])
