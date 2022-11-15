import logging
from typing import List, Optional

from pixl_ehr._queries import SQLQuery
from pixl_ehr.utils import env_var
import psycopg2 as pypg

logger = logging.getLogger("uvicorn")


class Database:
    """Fake database wrapper"""

    def __init__(
        self,
        db_name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
    ) -> None:

        connection_string = (
            f"dbname={db_name} user={username} password={password} host={host}"
        )
        self._connection = pypg.connect(connection_string)
        self._cursor = self._connection.cursor()


class QueryableDatabase(Database):
    def execute(self, query: SQLQuery) -> Optional[tuple]:
        """Execute an sql query"""

        # logger.debug(f"Running query: \n"
        #             f"{self._cursor.mogrify(str(query), vars=query.values).decode()}")

        self._cursor.execute(query=str(query), vars=query.values)
        row = self._cursor.fetchone()
        return None if row is None else tuple(row)

    def execute_or_raise(self, query: SQLQuery, error_str: str = "Failed") -> tuple:

        result = self.execute(query)

        if result is None:
            raise RuntimeError(error_str)

        return result


class WriteableDatabase(Database):
    def persist(self, template: str, values: List) -> None:
        """Execute an sql query"""

        self._cursor.execute(template, vars=values)
        self._connection.commit()


class EMAPStar(QueryableDatabase):
    def __init__(self) -> None:
        super().__init__(
            db_name=env_var("EMAP_UDS_NAME"),
            username=env_var("EMAP_UDS_USER"),
            password=env_var("EMAP_UDS_PASSWORD"),
            host=env_var("EMAP_UDS_HOST"),
        )

    def __repr__(self) -> str:
        return "EMAPStarDatabase"


class PIXLDatabase(WriteableDatabase):
    def __init__(self) -> None:
        super().__init__(
            db_name=env_var("PIXL_DB_NAME"),
            username=env_var("PIXL_DB_USER"),
            password=env_var("PIXL_DB_PASSWORD"),
            host=env_var("PIXL_DB_HOST"),
        )

    def __repr__(self) -> str:
        return "PIXLDatabase"
