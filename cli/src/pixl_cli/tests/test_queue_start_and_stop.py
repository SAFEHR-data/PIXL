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
import os
from pathlib import Path
from typing import Any

from click.testing import CliRunner
from pixl_cli.main import populate
from patient_queue.producer import PixlProducer


def test_populate_queue(queue_name: str = "test_populate") -> None:

    runner = CliRunner()
    result = runner.invoke(populate, args=["test.csv", "--queues", queue_name])
    assert result.exit_code == 0

# def test_down_queue(queue_name: str = "test_down") -> None:
#
#     runner = CliRunner()
#     _ = runner.invoke(populate, args=["test.csv", "--queues", queue_name])
#     _ = runner.invoke(stop, args=["--queues", queue_name])
#
#     with _RabbitMQContext() as rmq:
#         queue = rmq.channel.queue_declare(queue=queue_name)
#         assert queue.method.message_count == 0
#         rmq.channel.queue_delete(queue=queue_name)
#
#     state_path = Path(f"{queue_name}.state")
#     assert state_path.exists()
#     os.remove(state_path)
