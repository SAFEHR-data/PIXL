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
"""Subscriber for RabbitMQ"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aio_pika

from core.patient_queue.message import Message, deserialise

from ._base import PixlBlockingInterface, PixlQueueInterface

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from typing_extensions import Self

    from core.token_buffer.tokens import TokenBucket

logger = logging.getLogger(__name__)


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

    async def __aenter__(self) -> Self:
        """Establishes connection to queue."""
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        # Don't prefetch messages
        await self._channel.set_qos(prefetch_count=1)
        self._queue = await self._channel.declare_queue(self.queue_name)
        return self

    async def run(self, callback: Callable[[Message], Awaitable[None]]) -> None:
        """
        Creates loop that waits for messages from producer and processes them as
        they appear.
        :param callback: Method to be called when new message arrives that needs to
                         be processed. Must take a dictionary and return None.
        """
        async with self._queue.iterator() as queue_iter:
            # Pre-annotate the message type
            message: aio_pika.abc.AbstractIncomingMessage
            async for message in queue_iter:
                if not self.token_bucket.has_token:
                    await asyncio.sleep(0.01)
                    await message.reject(requeue=True)
                    continue

                pixl_message = deserialise(message.body)
                try:
                    await asyncio.sleep(0.01)  # Avoid very fast callbacks
                    await callback(pixl_message)
                except Exception:
                    logger.exception(
                        "Failed to process %s" "Not re-queuing message",
                        pixl_message,
                    )
                finally:
                    await message.ack()

    async def __aexit__(self, *args: object, **kwargs: Any) -> None:
        """Requirement for the asynchronous context manager"""


class PixlBlockingConsumer(PixlBlockingInterface):
    """Connector to RabbitMQ. Consumes messages from in blocks"""

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

        def callback(method: Any, properties: Any, body: Any) -> None:  # noqa: ARG001
            """Consume to file."""
            try:
                with Path.open(file_path, "a") as csv_file:
                    print(str(body.decode()), file=csv_file)
            except:  # noqa: E722
                logger.exception("Failed to consume")

        counter = 0
        for args in generator:
            if all(arg is None for arg in args):
                logger.info("Stopping")
                break
            callback(*args)
            counter += 1
        return counter
