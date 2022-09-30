import os
import psycopg2 as pypg

from typing import Optional
from pathlib import Path


def _env_var(key: str) -> str:
    """Get an environment variable and raise a helpful exception if it's not"""

    if (value := os.environ.get(key, None)) is None:
        raise RuntimeError(f"Failed to find ${key}. Ensure it is set as "
                           f"an environment variable")
    return value


class Database:
    """Fake database wrapper"""

    def __init__(self):

        self._connection = self._create_connection()
        self._cursor = self._connection.cursor()

    @staticmethod
    def _create_connection() -> "psycopg2.connection":

        connection_string = (
            f"dbname={_env_var('EMAP_UDS_NAME')} "
            f"user={_env_var('EMAP_UDS_USER')} "
            f"password={_env_var('EMAP_UDS_PASSWORD')} "
            f"host={_env_var('EMAP_UDS_HOST')}"
        )
        return pypg.connect(connection_string)


class SQLQuery:

    def __init__(self, filepath: Path, context: dict):

        self.values = []
        self._filepath = filepath
        self._lines = open(filepath, "r").readlines()
        self._replace_placeholders_and_populate_values(context)

    def __str__(self) -> str:
        return ''.join(self._lines)

    def _replace_placeholders_and_populate_values(self, context: dict) -> None:
        """
        Replace the placeholders in the file with those defined in the context.
        Placeholders must be in the :variable or ${{ }} formats. The former
        will be replaced with psycopg2 value replacement, with correct type
        casting. ${{ }} placeholders will be replaced as is string replacement
        """

        for i, line in enumerate(self._lines):
            if ":" not in line and "${{" not in line:
                continue

            for key, value in context.items():
                line = line.replace("${{ "+str(key)+" }}", str(value))

                n = line.count(f":{key}")
                self.values += n * [value]
                line = line.replace(f":{key}", "%s")

            if ":" in line.replace("::", "") or "${{" in line:
                raise RuntimeError("Had an insufficient context to replace "
                                   f"line {i} in {self._filepath}\n"
                                   f"{line}")
            self._lines[i] = line

        return None


class QueryableDatabase(Database):

    def execute(self, query: SQLQuery) -> Optional[tuple]:
        """Execute an sql query"""

        self._cursor.execute(query=str(query),
                             vars=query.values)
        row = self._cursor.fetchone()
        return row

    def execute_or_raise(self,
                         query: SQLQuery,
                         error_str: str = "Failed"
                         ) -> tuple:

        result = self.execute(query)

        if result is None:
            raise RuntimeError(error_str)

        return result
