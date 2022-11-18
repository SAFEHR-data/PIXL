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


def env_var(key: str) -> str:
    """Get an environment variable and raise a helpful exception if it's not set"""

    if (value := os.environ.get(key, None)) is None:
        raise RuntimeError(
            f"Failed to find ${key}. Ensure it is set as " f"an environment variable"
        )
    return value
