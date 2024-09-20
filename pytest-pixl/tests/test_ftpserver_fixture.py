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

import pytest
from conftest import TEST_DIR
from pytest_pixl.dicom import _create_default_json
from pytest_pixl.plugin import FtpHostAddress


@pytest.mark.pytester_example_path(
    str(TEST_DIR) + "/samples_for_fixture_tests/test_ftpserver_fixture"
)
def test_ftpserver_connection(pytester):
    """Test whether we can connect to the FTP server fixture"""
    pytester.copy_example("test_ftpserver_login.py")
    pytester.runpytest("-k", "test_ftpserver_login")


def test_create_default_json_file():
    """Test whether we can create a default JSON file"""
    filename_to_create = "test_json_file.json"
    _create_default_json(filename_to_create)
    assert Path(filename_to_create).exists()
    os.remove(filename_to_create)  # noqa: PTH107


def test_ftp_host_address():
    """Run FTP on localhost - docker containers do not need to access it"""
    assert FtpHostAddress.DOCKERHOST == FtpHostAddress.DOCKERHOST
