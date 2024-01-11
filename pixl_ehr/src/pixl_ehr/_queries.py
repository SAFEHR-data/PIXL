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
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class SQLQuery:
    def __init__(self, filepath: Path, context: dict) -> None:
        self.values: list[str] = []
        self._filepath = filepath
        self._lines = filepath.open().readlines()
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

            new_line = line
            for key, value in context.items():
                new_line = new_line.replace("${{ " + str(key) + " }}", str(value))

                n = new_line.count(f":{key}")
                self.values += n * [value]
                new_line = new_line.replace(f":{key}", "%s")

            if ":" in new_line.replace("::", "") or "${{" in new_line:
                msg = (
                    "Had an insufficient context to replace "
                    f"new_line {i} in {self._filepath}\n"
                    f"{new_line}"
                )
                raise RuntimeError(msg)
            self._lines[i] = new_line
