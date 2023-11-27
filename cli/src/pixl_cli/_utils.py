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
import os
from pathlib import Path


def clear_file(filepath: Path) -> None:
    """Clear the contents of a file"""
    Path.open(filepath, "w").close()


def string_is_non_empty(string: str) -> bool:
    """Does a string have more than just spaces and newlines?"""
    return len(string.split()) > 0


def remove_file_if_it_exists(filepath: Path) -> None:
    """If a file exists remove it"""
    if filepath.exists():
        os.remove(filepath)
