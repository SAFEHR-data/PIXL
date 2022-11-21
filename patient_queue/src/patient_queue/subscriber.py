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

import aio_pika
import logging
from typing import Callable

from pixl_ehr._processing import process_message
from token_buffer import TokenBucket

LOGGER = logging.getLogger(__name__)


class PixlConsumer:
    """Connector to RabbitMQ. Consumes messages from a queue that specify patients for which EHR demographic data needs to be retrieved ."""
    def __init__(self, queue: str, port: int, user: str, password: str) -> None:
        """
        Creating connection to RabbitMQ queue.
        :param queue: Name of the queue to connect to.
        :param port: Port the queue is provided through (i.e. RabbitMQ port)
        :param user: Which user to use for connection
        :param password: Which password to use for the connection
        """
        self._url = f"amqp://{user}:{password}@{queue}:{port}/"
        self._create_connection(queue=queue)

    async def _create_connection(self, queue: str):
        self._connection = await aio_pika.connect(self._url)
        async with self._connection:
            self._channel = await self._connection.channel()
            self._queue = await self._channel.declare_queue(queue)

    async def run(self, token_buffer: TokenBucket, callback: Callable = process_message) -> None:
        """Creates loop that waits for messages from producer and processes them as they appear.
        :param token_buffer: token buffer for EHR queue
        :param callback: method to be called when new message arrives that needs to be processed
        """
        async with self._queue.iterator() as queue_iter:
            async for message in queue_iter:

                try:
                    if token_buffer.has_token:
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
