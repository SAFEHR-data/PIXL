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
"""Test copying of OMOP ES data for later export."""
import datetime

import pytest


def test_new_project_copies(omop_files, resources):
    """
    Given a valid export directory and hasn't been exported before
    When copy to exports is run
    Then the public files should be copied and symlinked to the latest export directory
    """
    # ARRANGE
    input_dir = resources / "omop"
    project_name = "Really great cool project"
    input_date = datetime.datetime.fromisoformat("2020-06-10T18:00:00")
    # ACT
    omop_files.copy_to_exports(input_dir, project_name, input_date)
    # ASSERT
    output_base = omop_files.export_dir / "really-great-cool-project"

    # check public files copied
    specific_export_dir = (
        output_base / "all_extracts" / "omop" / "2020-06-10t18-00-00" / "public"
    )
    assert (specific_export_dir).exists()
    expected_files = [x.stem for x in (input_dir / "public").glob("*.parquet")]
    output_files = [x.stem for x in (specific_export_dir).glob("*.parquet")]
    assert expected_files == output_files
    # check that symlinked files exist
    symlinked_dir = output_base / "latest" / "omop" / "public"
    symlinked_files = list(symlinked_dir.glob("*.parquet"))
    assert expected_files == [x.stem for x in symlinked_files]
    assert symlinked_dir.is_symlink()


def test_second_export(omop_files, resources):
    """
    Given one export already exists for the project
    When a second export with a different timestamp is run for the same project
    Then there should be two export directories in the all_extracts dir,
      and the symlinked dir should point to the most recently copied dir
    """
    # ARRANGE
    input_dir = resources / "omop"
    project_name = "Really great cool project"
    first_export_datetime = datetime.datetime.fromisoformat("2020-06-10T18:00:00")
    omop_files.copy_to_exports(input_dir, project_name, first_export_datetime)
    second_export_datetime = datetime.datetime.fromisoformat("2020-07-10T18:00:00")

    # ACT
    omop_files.copy_to_exports(input_dir, project_name, second_export_datetime)

    # ASSERT
    output_base = omop_files.export_dir / "really-great-cool-project"
    specific_export_dir = (
        output_base / "all_extracts" / "omop" / "2020-07-10t18-00-00" / "public"
    )
    assert specific_export_dir.exists()
    # check that symlinked files are the most recent export
    symlinked_dir = output_base / "latest" / "omop" / "public"
    assert symlinked_dir.readlink() == specific_export_dir
    previous_export_dir = (
        output_base / "all_extracts" / "omop" / "2020-06-10t18-00-00" / "public"
    )
    assert symlinked_dir.readlink() != previous_export_dir
    assert previous_export_dir.exists()


def test_project_with_no_public(omop_files, resources):
    """
    Given an export directory which has no "public" subdirectory
    When copy to exports is run
    Then an assertion error will be raised
    """
    input_dir = resources
    project_name = "Really great cool project"
    input_date = datetime.datetime.fromisoformat("2020-06-10T18:00:00")
    with pytest.raises(FileNotFoundError) as error_info:
        omop_files.copy_to_exports(input_dir, project_name, input_date)

    assert error_info.match("Could not find public")
