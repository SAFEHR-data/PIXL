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
import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import aio_pika

from core.token_buffer.tokens import TokenBucket

from ._base import PixlBlockingInterface, PixlQueueInterface

LOGGER = logging.getLogger(__name__)


class PixlConsumer(PixlQueueInterface):
    """Connector to RabbitMQ. Consumes messages from a queue"""

    def __init__(self, queue_name: str, token_bucket: TokenBucket) -> None:
        """
        Creating connection to RabbitMQ queue
        :param token_bucket: Token bucket for EHR queue
        """
        super().__init__(queue_name=queue_name)
        self.token_bucket = token_bucket

    @property
    def _url(self) -> str:
        return f"amqp://{self._username}:{self._password}@{self._host}:{self._port}/"

    async def __aenter__(self) -> "PixlConsumer":
        """Establishes connection to queue."""
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        self._queue = await self._channel.declare_queue(self.queue_name)
        return self

    async def run(self, callback: Callable[[bytes], Awaitable[None]]) -> None:
        """
        Creates loop that waits for messages from producer and processes them as
        they appear.
        :param callback: Method to be called when new message arrives that needs to
                         be processed. Must take a dictionary and return None.
        """
        async with self._queue.iterator() as queue_iter:
            async for message in queue_iter:
                if not self.token_bucket.has_token:
                    await asyncio.gather(
                        message.reject(requeue=True),
                        asyncio.sleep(1e-3),
                    )
                    continue

                # Messages need to be acknowledged before a callback otherwise
                # RabbitMQ can close the connection. As all messages that raise
                # exceptions aren't returned to the queue we're safe to do this
                await message.ack()

                try:
                    await asyncio.gather(
                        callback(message.body),
                        asyncio.sleep(1e-3),  # Avoid very fast callbacks
                    )
                except Exception as e:
                    LOGGER.error(
                        f"Failed to process {message.body.decode()} due to\n{e}\n"
                        f"Not re-queuing message"
                    )

    async def __aexit__(self, *args: object, **kwargs: Any) -> None:
        """Requirement for the asynchronous context manager"""


class PixlBlockingConsumer(PixlBlockingInterface):
    def consume_all(self, file_path: Path, timeout_in_seconds: int = 5) -> int:
        """
        Retrieving all messages still on queue and save them in a specified CSV file.
        :param timeout_in_seconds: Causes shutdown after the timeout (specified in secs)
        :param file_path: path to where remaining messages should be written
                          before shutdown
        :returns: the number of messages that have been consumed and written to the
                  specified file.
        """
        generator = self._channel.consume(
            queue=self.queue_name,
            auto_ack=True,
            inactivity_timeout=timeout_in_seconds,  # Yields (None, None, None) after
        )

        def callback(method: Any, properties: Any, body: Any) -> None:
            try:
                with Path.open(file_path, "a") as csv_file:
                    print(str(body.decode()), file=csv_file)
            except:
                LOGGER.debug("Failed to consume")

        counter = 0
        for args in generator:
            if all(arg is None for arg in args):
                LOGGER.info("Stopping")
                break
            callback(*args)
            counter += 1
        return counter
