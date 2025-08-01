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

from __future__ import annotations

import datetime

import pytest

from core.exports import ParquetExport


def test_new_project_copies(omop_resources, export_dir):
    """
    Given a valid export directory and hasn't been exported before
    When copy to exports is run
    Then the public files should be copied and symlinked to the latest export directory
    """
    # ARRANGE
    input_dir = omop_resources / "omop"
    project_name = "Really great cool project"
    input_date = datetime.datetime.fromisoformat("2020-06-10T18:00:00")
    omop_files = ParquetExport(project_name, input_date, export_dir)
    # ACT
    omop_files.copy_to_exports(input_dir)
    # ASSERT
    output_base = omop_files.export_dir / "really-great-cool-project"

    # check public files copied
    specific_export_dir = output_base / "all_extracts" / "2020-06-10t18-00-00" / "omop" / "public"
    assert (specific_export_dir).exists()
    # (glob sort order is not guaranteed)
    expected_files = sorted([x.stem for x in (input_dir / "public").glob("*.parquet")])
    output_files = sorted([x.stem for x in (specific_export_dir).glob("*.parquet")])
    assert expected_files == output_files
    # check that symlinked files exist
    symlinked_dir = output_base / "latest"
    assert symlinked_dir.is_symlink()
    symlinked_dir_public = symlinked_dir / "omop" / "public"
    symlinked_files = list(symlinked_dir_public.glob("*.parquet"))
    assert expected_files == sorted([x.stem for x in symlinked_files])


def test_second_export(omop_resources, export_dir):
    """
    Given one export already exists for the project
    When a second export with a different timestamp is run for the same project
    Then there should be two export directories in the all_extracts dir,
      and the symlinked dir should point to the most recently copied dir
    """
    # ARRANGE
    input_dir = omop_resources / "omop"
    project_name = "Really great cool project"
    first_export_datetime = datetime.datetime.fromisoformat("2020-06-10T18:00:00")

    omop_files = ParquetExport(project_name, first_export_datetime, export_dir)
    omop_files.copy_to_exports(input_dir)
    second_export_datetime = datetime.datetime.fromisoformat("2020-07-10T18:00:00")

    omop_files = ParquetExport(project_name, second_export_datetime, export_dir)

    # ACT
    omop_files.copy_to_exports(input_dir)

    # ASSERT
    output_base = omop_files.export_dir / "really-great-cool-project"
    specific_export_dir = output_base / "all_extracts" / "2020-07-10t18-00-00" / "omop" / "public"
    assert specific_export_dir.is_dir()
    # check that symlinked files are the most recent export
    symlinked_dir = output_base / "latest" / "omop" / "public"
    # samefile does follow symlinks, even though the docs are vague on this
    assert symlinked_dir.samefile(specific_export_dir)
    previous_export_dir = output_base / "all_extracts" / "2020-06-10t18-00-00" / "omop" / "public"
    assert not symlinked_dir.samefile(previous_export_dir)
    assert previous_export_dir.exists()


def test_project_with_no_public(omop_resources, export_dir):
    """
    Given an export directory which has no "public" subdirectory
    When copy to exports is run
    Then an assertion error will be raised
    """
    input_dir = omop_resources
    project_name = "Really great cool project"
    input_date = datetime.datetime.fromisoformat("2020-06-10T18:00:00")
    omop_files = ParquetExport(project_name, input_date, export_dir)
    with pytest.raises(FileNotFoundError):
        omop_files.copy_to_exports(input_dir)
