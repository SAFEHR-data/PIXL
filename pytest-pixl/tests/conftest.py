#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
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

# Avoid running samples for fixture tests directly with pytest
collect_ignore = ["samples_for_fixture_tests"]

pytest_plugins = ["pytester"]

TEST_DIR = Path(__file__).parent

os.environ["FTP_HOST"] = "localhost"
os.environ["FTP_USER_NAME"] = "pixl_user"
os.environ["FTP_USER_PASSWORD"] = "longpassword"  # noqa: S105 Hardcoding password
os.environ["FTP_PORT"] = "20021"
