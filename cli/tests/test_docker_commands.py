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
"""Docker commands tests"""

import pytest
from click.testing import CliRunner
from pixl_cli.main import PIXL_ROOT, cli


@pytest.fixture(autouse=True)
def _change_working_directory(monkeypatch) -> None:
    """
    Change the working directory to the PIXL root directory.
    This is required to spin up the docker containers.
    """
    monkeypatch.setenv("ENV", "test")
    monkeypatch.chdir(PIXL_ROOT)


@pytest.fixture()
def default_args() -> list[str]:
    """Default arguments for the docker commands."""
    return ["--dry-run", "--env-file=test/.env"]


def test_pixl_up_works(default_args):
    """Test that pixl up works and attempts to spin up docker containers."""
    runner = CliRunner()
    result = runner.invoke(cli, args=["dc", "up", *default_args])
    assert result.exit_code == 0


def test_pixl_down_works(default_args):
    """Test that pixl up works and attempts to spin up docker containers."""
    runner = CliRunner()
    result = runner.invoke(cli, args=["dc", "down", *default_args])
    assert result.exit_code == 0


def test_pixl_down_warns_on_volumes(monkeypatch, default_args):
    """Test that a warning is displayed when attempting to remove volumes in production."""
    monkeypatch.setenv("ENV", "prod")

    runner = CliRunner()
    result = runner.invoke(cli, args=["dc", "down", *default_args, "--volumes"])

    assert result.exit_code == 0
    assert "WARNING: Attempting to remove volumes in production." in result.output
    assert "Are you sure you want to remove the volumes?" in result.output
    assert "Running 'docker compose down' without removing volumes." in result.output
