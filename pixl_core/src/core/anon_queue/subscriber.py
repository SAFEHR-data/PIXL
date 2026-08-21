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

from typing import TYPE_CHECKING, Any

import pika
from decouple import config

from core.anon_queue._base import PixlQueueInterface
from core.anon_queue.message import deserialise
from core.exceptions import (
    PixlDiscardError,
    PixlOutOfHoursError,
    PixlRequeueMessageError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Self

    from core.anon_queue.message import AnonymisationMessage

import time

from loguru import logger


class AnonymisationPixlConsumer(PixlQueueInterface):
    """Connector to RabbitMQ. Consumes messages from anonymisation queue"""

    def __init__(
        self,
        queue_name: str,
        callback: Callable[[AnonymisationMessage], Awaitable[None]],
    ) -> None:
        """Creating connection to RabbitMQ queue"""
        super().__init__(queue_name=queue_name)
        self._callback = callback

    @property
    def _url(self) -> str:
        return f"amqp://{self._username}:{self._password}@{self._host}:{self._port}/"

    def __enter__(self) -> Self:
        """Establishes connection to queue."""
        self._connection = pika.BlockingConnection(pika.URLParameters(self._url))
        self._channel = self._connection.channel()
        # Set number of messages in flight
        max_in_flight = config("PIXL_MAX_MESSAGES_IN_FLIGHT", cast=int)
        logger.info("Pika will consume up to {} messages concurrently", max_in_flight)
        self._channel.basic_qos(prefetch_count=max_in_flight)
        self._queue = self._channel.queue_declare(
            queue=self.queue_name,
            durable=True,
        )
        return self

    def _process_message(self, message: Any) -> None:

        pixl_message: AnonymisationMessage = deserialise(message.body)
        logger.debug("Picked up from queue: {}", pixl_message.identifier)
        try:
            self._callback(pixl_message)
        except PixlRequeueMessageError as requeue:
            logger.trace("Requeue message: {} from {}", pixl_message.identifier, requeue)
            time.sleep(1)
            message.reject(requeue=True)
        except PixlOutOfHoursError as nack_requeue:
            logger.trace(
                "Nack and requeue message: {} from {}", pixl_message.identifier, nack_requeue
            )
            time.sleep(10)
            message.nack(requeue=True)
        except PixlDiscardError as exception:
            logger.warning("Failed message {}: {}", pixl_message.identifier, exception)
            (message.ack())  # ack so that we can see rate of message processing in rabbitmq admin
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to process {}. Not re-queuing message",
                pixl_message.identifier,
            )
            (message.ack())  # ack so that we can see rate of message processing in rabbitmq admin
        else:
            logger.success("Finished message {}", pixl_message.identifier)
            message.ack()

    def run(self) -> None:
        """Processes messages from queue."""
        self._channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=self._process_message,
            auto_ack=False,
        )
        self._channel.start_consuming()

    def __exit__(self, *args: object, **kwargs: Any) -> None:
        """Requirement for the context manager"""
        if self._channel is not None and self._channel.is_open:
            self._channel.close()

        if self._connection is not None and self._connection.is_open:
            self._connection.close()
