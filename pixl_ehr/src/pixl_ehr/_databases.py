import psycopg2 as pypg
import logging

from pixl_ehr.utils import env_var
from typing import Optional

logger = logging.getLogger("uvicorn")


class Database:
    """Fake database wrapper"""

    db_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    host: Optional[str] = None

    def __init__(self):

        connection_string = (
            f"dbname={self.db_name} "
            f"user={self.username} "
            f"password={self.password} "
            f"host={self.host}"
        )
        self._connection = pypg.connect(connection_string)
        self._cursor = self._connection.cursor()


class QueryableDatabase(Database):

    def execute(self, query: "SQLQuery") -> Optional[tuple]:
        """Execute an sql query"""

        logger.debug(f"Running query: \n"
                     f"{self._cursor.mogrify(str(query), vars=query.values).decode()}")

        self._cursor.execute(query=str(query),
                             vars=query.values)
        row = self._cursor.fetchone()
        return row

    def execute_or_raise(self,
                         query: "SQLQuery",
                         error_str: str = "Failed"
                         ) -> tuple:

        result = self.execute(query)

        if result is None:
            raise RuntimeError(error_str)

        return result


class EMAPStar(QueryableDatabase):

    db_name = env_var('EMAP_UDS_NAME')
    username = env_var('EMAP_UDS_USER')
    password = env_var('EMAP_UDS_PASSWORD')
    host = env_var('EMAP_UDS_HOST')
