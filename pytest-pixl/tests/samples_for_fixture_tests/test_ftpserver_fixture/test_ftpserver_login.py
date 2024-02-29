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
"""Fixture test example to login to the FTPS server and do a simple file transfer."""

from pathlib import Path

from core.uploader.ftps import _connect_to_ftp

TEST_FILE_CONTENT = "test text"
TEST_FILENAME = "testfile.txt"


def test_ftpserver_login(tmp_path, ftps_server):
    """Tests if we can connect to the FTPS server and write a test file."""
    # Arrange
    file_path_local = tmp_path / TEST_FILENAME
    file_path_local.write_text(TEST_FILE_CONTENT, encoding="utf-8")

    # Act
    ftp = _connect_to_ftp()
    # Upload testfile to the FTPS server
    with file_path_local.open("rb") as f:
        ftp.storbinary("STOR " + TEST_FILENAME, f)

    # Assert
    expected_file_path = Path(ftps_server.home_dir) / TEST_FILENAME
    assert expected_file_path.exists()
    assert expected_file_path.read_text() == TEST_FILE_CONTENT

    # Clean up
    ftp.quit()
