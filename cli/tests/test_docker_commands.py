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

from click.testing import CliRunner
from pixl_cli._docker_commands import down, up


def test_pixl_up_works():
    """Test that pixl up works and attempts to spin up docker containers."""
    runner = CliRunner()
    result = runner.invoke(up, args=["--dry-run"])
    assert result.exit_code == 0
    assert result.output == ""


def test_pixl_down_works():
    """Test that pixl up works and attempts to spin up docker containers."""
    runner = CliRunner()
    result = runner.invoke(down, args=["--dry-run"])
    assert result.exit_code == 0
    assert result.output == ""


def test_pixl_down_warns_on_volumes(monkeypatch):
    """Test that a warning is displayed when attempting to remove volumes in production."""
    runner = CliRunner()

    monkeypatch.setenv("ENV", "prod")
    result = runner.invoke(down, args=["--dry-run", "--volumes"])

    assert result.exit_code == 0
    assert "WARNING: Attempting to remove volumes in production." in result.output
    assert "Are you sure you want to remove the volumes?" in result.output
    assert "Running 'docker compose down' without removing volumes." in result.output
