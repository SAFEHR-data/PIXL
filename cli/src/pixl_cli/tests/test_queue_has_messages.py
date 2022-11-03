import os

import pika
from click.testing import CliRunner

from pathlib import Path
from pixl_cli.main import (
    populate,
    queue_is_up,
    create_connection
)


def test_queue_is_up() -> None:
    assert queue_is_up()


def _connection_and_queue(queue_name: str) -> tuple:


class _RabbitMQContext:

    __test__ = False

    def __init__(self):
        self.connection = create_connection()
        self.channel = self.connection.channel()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.close()


def test_populate_queue(queue_name: str = "test_populate") -> None:

    csv_path = Path("test.csv")
    assert csv_path.exists()

    runner = CliRunner()
    result = runner.invoke(populate, [str(csv_path), "--queues", queue_name])

    assert result.exit_code == 0

    with _RabbitMQContext() as rmq:
        queue = rmq.channel.queue_declare(queue=queue_name)
        assert queue.method.message_count == 1
        rmq.channel.queue_delete(queue=queue_name)

    connection.close()


def test_down_queue(queue_name: str = "test_down") -> None

