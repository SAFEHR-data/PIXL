#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
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
from pathlib import Path
from typing import Any, Callable, Coroutine

import aio_pika
import pika

from token_buffer import TokenBucket

LOGGER = logging.getLogger(__name__)


class PixlConsumer:
    """
    Connector to RabbitMQ. Consumes messages from a queue that specify patients for
    which EHR demographic data needs to be retrieved.
    """

    def __init__(
        self, queue: str, port: int, token_bucket: TokenBucket, host: str = "queue"
    ) -> None:
        """
        Creating connection to RabbitMQ queue.
        :param queue: Name of the queue to connect to.
        :param port: Port the queue is provided through (i.e. RabbitMQ port)
        :param token_bucket: Token bucket for EHR queue
        :param host: Name of the machine RabbitMQ is running on; cannot be
                     hardcoded for tests.
                     Default is name of Docker container as configured.
        """
        self.token_bucket = token_bucket
        self._url = (
            f"amqp://{os.environ['RABBITMQ_DEFAULT_USER']}"
            f":{os.environ['RABBITMQ_DEFAULT_PASS']}@{host}:{port}/"
        )
        self._queue_name = queue

    async def __aenter__(self) -> "PixlConsumer":
        """Establishes connection to queue."""
        self._connection = await aio_pika.connect(self._url)
        self._channel = await self._connection.channel()
        self._queue = await self._channel.declare_queue(self._queue_name)
        return self

    def __await__(self) -> Coroutine[Any, Any, "PixlConsumer"]:
        """
        Await redirects to entering of context.
        :return:
        """
        return self.__aenter__()

    async def run(self, callback: Callable) -> None:
        """Creates loop that waits for messages from producer and processes them as
           they appear.
        :param callback: method to be called when new message arrives that needs to
                         be processed
        """
        async with self._queue.iterator() as queue_iter:
            async for message in queue_iter:
                try:
                    if self.token_bucket is not None:
                        if self.token_bucket.has_token:
                            callback(message.body)
                            await message.ack()
                        else:
                            await message.reject(requeue=True)
                except Exception as e:  # noqa
                    LOGGER.error(
                        f"Failed to process {message.body.decode()} due to\n{e}\n"
                        f"Not re-queuing message"
                    )
                    await message.reject(requeue=False)

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        At the moment only here as a requirement for the asynchronous context
        manager.
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        pass


class PixlBlockingConsumer:
    def __init__(
        self, host: str, port: int, queue_name: str, user: str, password: str
    ) -> None:
        """
        Initialising RabbitMQ service configuration for connection.
        :param str host: URL for the RabbitMQ service
        :param int port: Port on which RabbitMQ service is running
        :param str queue_name: Name of the queue this producer is to publish on
        :param user: RabbitMQ user name as configured for queue
        :param password: RabbitMQ user password as configured for queue
        """
        self._connection = None
        self._channel = None
        self._queue = None
        self.queue_name = queue_name
        self._host = host
        self._port = port
        self._user = user
        self._password = password

    def __enter__(self) -> "PixlBlockingConsumer":
        """Establishes connection to RabbitMQ service."""
        credentials = pika.PlainCredentials(self._user, self._password)
        params = pika.ConnectionParameters(self._host, self._port, "/", credentials)
        if self._connection is None or self._connection.is_closed:  # noqa
            self._connection = pika.BlockingConnection(params)

            if self._channel is None or self._channel.is_closed:
                self._channel = self._connection.channel()  # type: ignore
            self._queue = self._channel.queue_declare(queue=self.queue_name)  # type: ignore
        LOGGER.info(f"Connected to {self._queue}")
        return self

    def consume_all(self, file_path: Path, timeout_in_seconds: int = 5) -> int:
        """
        Retrieving all messages still on queue and save them in a specified CSV file.
        :param timeout_in_seconds: Causes shutdown after the timeout (specified in secs)
        :param file_path: path to where remaining messages should be written
                          before shutdown
        :returns: the number of messages that have been consumed and written to the
                  specified file.
        """
        generator = self._channel.consume(  # type: ignore
            queue=self.queue_name,
            auto_ack=True,
            inactivity_timeout=timeout_in_seconds,
            # Yields (None, None, None) after this
        )

        def callback(method: Any, properties: Any, body: Any) -> None:
            try:
                with open(file_path, "a") as csv_file:
                    csv_file.write(str(body) + "\n")
            except:  # noqa
                LOGGER.debug("Failed to consume")

        counter = 0
        for args in generator:
            if all(arg is None for arg in args):
                LOGGER.info("Stopping")
                break
            callback(*args)
            counter += 1
        return counter

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Shutdown the connection to RabbitMQ service.
        :return:
        """
        self._channel.close()  # type: ignore
        self._connection.close()  # type: ignore
