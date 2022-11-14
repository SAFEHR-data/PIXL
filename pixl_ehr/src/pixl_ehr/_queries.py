from pathlib import Path
from typing import List


class SQLQuery:
    def __init__(self, filepath: Path, context: dict):

        self.values: List[str] = []
        self._filepath = filepath
        self._lines = open(filepath, "r").readlines()
        self._replace_placeholders_and_populate_values(context)

    def __str__(self) -> str:
        return "".join(self._lines)

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
                line = line.replace("${{ " + str(key) + " }}", str(value))

                n = line.count(f":{key}")
                self.values += n * [value]
                line = line.replace(f":{key}", "%s")

            if ":" in line.replace("::", "") or "${{" in line:
                raise RuntimeError(
                    "Had an insufficient context to replace "
                    f"line {i} in {self._filepath}\n"
                    f"{line}"
                )
            self._lines[i] = line
