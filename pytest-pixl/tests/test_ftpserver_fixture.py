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
import pytest


@pytest.mark.pytester_example_path("tests/samples_for_fixture_tests/test_ftpserver_fixture")
def test_ftpserver_connection(pytester):
    """Test whether we can connect to the FTP server fixture"""
    pytester.copy_example("test_ftpserver_login.py")
    pytester.runpytest("-k", "test_ftpserver_login")
