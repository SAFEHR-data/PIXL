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
import logging
import os
from typing import Any

import pika

LOGGER = logging.getLogger(__name__)


class PixlQueueInterface:
    def __init__(
        self,
        queue_name: str,
        host: str = "localhost",
        port: int = 5672,
        username: str = "guest",
        password: str = "guest",
    ) -> None:
        """
        Generic RabbitMQ interface. Environment variables RABBITMQ_<X> take precedence
        over arguments

        :param queue_name: Name of the queue this interfaces to
        :param host: Hostname of the RabbitMQ service.
        :param port: Port on which RabbitMQ service is running.
        :param username: RabbitMQ username as configured for queue.
        :param password: RabbitMQ user password as configured for queue
        """
        self.queue_name = queue_name

        self._host = os.environ.get("RABBITMQ_HOST", default=host)
        self._port = int(os.environ.get("RABBITMQ_PORT", default=port))
        self._username = os.environ.get("RABBITMQ_USERNAME", default=username)
        self._password = os.environ.get("RABBITMQ_PASSWORD", default=password)

        self._connection: Any = None
        self._channel: Any = None
        self._queue: Any = None


class PixlBlockingInterface(PixlQueueInterface):
    def __enter__(self) -> Any:
        """Establishes connection to RabbitMQ service."""
        params = pika.ConnectionParameters(
            host=self._host,
            port=self._port,
            credentials=pika.PlainCredentials(self._username, self._password),
        )

        if self._connection is None or self._connection.is_closed:
            self._connection = pika.BlockingConnection(params)

            if self._channel is None or self._channel.is_closed:
                self._channel = self._connection.channel()
            self._queue = self._channel.queue_declare(queue=self.queue_name)

        LOGGER.info(f"Connected to {self._queue}")
        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        """Shutdown the connection to RabbitMQ service."""
        self._channel.close()
        self._connection.close()

    @property
    def connection_open(self) -> bool:
        return bool(self._connection.is_open)

    @property
    def message_count(self) -> int:
        try:
            return int(self._queue.method.message_count)
        except (ValueError, TypeError):
            LOGGER.error("Failed to determine the number of messages. Returning 0")
            return 0
