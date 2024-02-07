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
from __future__ import annotations

from typing import TYPE_CHECKING

import pixl_cli.main
from click.testing import CliRunner
from core.patient_queue.producer import PixlProducer
from pixl_cli.main import populate

if TYPE_CHECKING:
    from pathlib import Path

    from core.patient_queue.message import Message


def test_populate_queue_parquet(
    monkeypatch, resources: Path, queue_name: str = "test_populate"
) -> None:
    """Checks that patient queue can be populated without error."""
    omop_parquet_dir = str(resources / "omop")
    runner = CliRunner()

    # mock producer
    class MockProducer(PixlProducer):
        def __enter__(self) -> PixlProducer:
            return self

        def __exit__(self, *args: object, **kwargs) -> None:
            return

        def publish(self, messages: list[Message]) -> None:  # noqa: ARG002 don't access messages
            return

    monkeypatch.setattr(pixl_cli.main, "PixlProducer", MockProducer)

    result = runner.invoke(populate, args=[omop_parquet_dir, "--queues", queue_name])
    assert result.exit_code == 0
