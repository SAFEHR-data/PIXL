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
"""Tests for check_env function of CLI."""

from pathlib import Path

from click.testing import CliRunner
from pixl_cli.main import check_env

SAMPLE_ENV_FILE = Path(__file__).parents[2] / ".env.sample"


def test_check_env():
    """
    Test that the check_env command runs without error.
    - check_env works
    - current test env file matches the sample env file
    """
    runner = CliRunner()
    result = runner.invoke(check_env)
    assert result.exit_code == 0


def test_check_env_fails(tmp_path):
    """
    Test that check_env fails when the current test env file does not match the sample env file.
    """  # noqa: D200 either this or it's 102 chars
    tmp_sample_env_file = tmp_path / ".env.sample"
    tmp_sample_env_file.write_text("NONEXISTENT_VARIABLE=")

    runner = CliRunner()
    result = runner.invoke(check_env, str(tmp_sample_env_file))
    assert result.exit_code != 0
