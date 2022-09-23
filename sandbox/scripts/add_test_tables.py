"""
Adds fake data to a database resembling the EMAP star scheme, albeit a
truncated version. A postgres instance should be up and running before running
this script, which requires environment variables (e.g. POSTGRES_USER) to be
set
"""
import pandas as pd

from typing import List
from datetime import datetime, date
from core import Database, _env_var
from test_data import ACCESSION_NUMBERS, MRNs


schema_structure = {
    "hospital_visit": {
        "hospital_visit_id": "bigint",
        "mrn_id": "bigint",
    },
    "visit_observation": {
        "hospital_visit_id": "bigint",
        "visit_observation_id": "bigint",
        "visit_observation_type_id": "bigint",
        "value_as_real": "double precision",
        "valid_from": "timestamptz"
    },
    "visit_observation_type": {
        "visit_observation_type_id": "bigint",
        "name": "varchar",
    },
    "core_demographic": {
        "core_demographic_id": "bigint",
        "mrn_id": "bigint",
        "date_of_birth": "date",
        "sex": "varchar",
        "ethnicity": "varchar"
    },
    "lab_result": {
        "lab_result_id": "bigint",
        "lab_order_id": "bigint"
    },
    "lab_sample": {
        "lab_sample_id": "bigint",
        "mrn_id": "bigint",
        "external_lab_number": "varchar"
    },
    "mrn": {
        "mrn_id": "bigint",
        "mrn": "varchar",
        "research_opt_out": "boolean"
    }
}


class Table(pd.DataFrame):

    def __init__(self, name: str, data: dict):
        super().__init__(data=self._convert_strings_to_datetimes(name, data))
        self.name = str(name)

    def col_name_to_name_and_sql_type(self, col_name: str) -> str:
        return f"{col_name} {schema_structure[self.name][col_name]}"

    @property
    def columns(self) -> List[str]:
        """Pandas doesn't let you have a column called name, helpfully. So
        strip any _ from a _name column"""
        return [s if s != '_name' else 'name' for s in super().columns]

    @staticmethod
    def _convert_strings_to_datetimes(table_name: str, data: dict) -> dict:
        """Convert any strings to dates or datetimes"""

        for col_name, sql_col_type in schema_structure[table_name].items():

            if sql_col_type not in ('date', 'timestamptz'):
                continue  # No transformation needed

            function = (date.fromisoformat if sql_col_type == 'date'
                        else datetime.fromisoformat)

            data[col_name] = [function(v) for v in data[col_name]]

        return data


class FakeDatabase(Database):
    """Fake database wrapper"""

    @property
    def schema_name(self) -> str:
        return _env_var("SCHEMA_NAME")

    def create_schema(self) -> None:
        """Create the database schema"""

        self._cursor.execute(f"DROP SCHEMA IF EXISTS {self.schema_name} CASCADE;")
        self._cursor.execute(f"CREATE SCHEMA {self.schema_name}"
                             f" AUTHORIZATION {_env_var('POSTGRES_USER')};")

    def create_empty_table_for(self, table: Table) -> None:
        """Create a table for a set of data. Drop it if it exists"""

        cols = ",".join([table.col_name_to_name_and_sql_type(c)
                         for c in table.columns])

        self._cursor.execute(
            f"CREATE TABLE {self.schema_name}.{table.name}"
            f"({table.name}_id serial PRIMARY KEY, {cols});"
        )

    def add(self, table: Table) -> None:
        """Addd a table to the schema"""
        print(f"Adding table: {table.name}")
        self.create_empty_table_for(table)

        cols = ",".join(table.columns)
        vals = ",".join("%s" for _ in range(len(table.columns)))

        for _, row in table.astype('object').iterrows():

            self._cursor.execute(
                f"INSERT INTO {self.schema_name}.{table.name} ({cols}) VALUES ({vals})",
                row.values,
            )

        self._connection.commit()


def main():

    # Note: the following data is hard coded, but could be easily generated
    # e.g. with Faker
    tables = [
        Table("hospital_visit",
              data={
                  "mrn_id": [1, 2]
                  }),
        Table("visit_observation",
              data={
                  "hospital_visit_id": [1, 1, 1, 2],
                  "visit_observation_type_id": [1, 2, 3, 3],
                  "value_as_real": [100, 60, 4, 6],
                  "valid_from": ['2021-02-01', '2021-02-02', '2022-02-03', '2022-01-01']
                  }),
        Table("visit_observation_type",
              data={
                  "_name": ["HEIGHT", "WEIGHT", "R GLASGOW COMA SCALE SCORE"],
              }),
        Table("core_demographic",
              data={
                "mrn_id": [0, 1],
                "date_of_birth": ['2022-01-01', '2022-02-01'],
                "sex": ['F', 'M'],
                "ethnicity": ['X', 'Y']
        }),
        Table("mrn",
              data={
                  "mrn": MRNs,
                  "research_opt_out": [False for _ in range(len(MRNs))]
              }),
        Table("lab_sample",
              data={
                  "mrn_id": list(range(len(ACCESSION_NUMBERS))),
                  "external_lab_number": ACCESSION_NUMBERS
              }),
    ]

    db = FakeDatabase()
    db.create_schema()

    for table in tables:
        db.add(table)

    print("Successfully created fake tables")
    return None


if __name__ == "__main__":
    main()
