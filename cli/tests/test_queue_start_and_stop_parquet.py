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
"""Patient queue tests"""

from pathlib import Path

from click.testing import CliRunner
from pixl_cli.main import populate, queue_is_up, stop


def test_populate_queue_parquet(resources, queue_name: str = "test_populate") -> None:
    """Checks that patient queue can be populated without error."""
    omop_parquet_dir = resources / "omop"
    runner = CliRunner()
    result = runner.invoke(
        populate, args=["--queues", queue_name, "--parquet-dir", omop_parquet_dir]
    )
    assert result.exit_code == 0


def test_down_queue_parquet(resources, queue_name: str = "test_down") -> None:
    """
    Checks that after the queue has been sent a stop signal,
    the queue has been emptied.
    """
    omop_parquet_dir = resources / "omop"
    runner = CliRunner()
    _ = runner.invoke(populate, args=["--queues", queue_name, "--parquet-dir", omop_parquet_dir])
    _ = runner.invoke(stop, args=["--queues", queue_name])

    state_path = Path(f"{queue_name}.state")
    assert state_path.exists()
    Path.unlink(state_path)


def test_queue_is_up() -> None:
    """Checks whether status of queue can be asserted correctly."""
    assert queue_is_up()
