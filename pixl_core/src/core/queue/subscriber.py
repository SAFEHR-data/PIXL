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
import time
from functools import partial
from typing import TYPE_CHECKING, Any

import aio_pika
import pika
from decouple import config
from opentelemetry.context import get_current

from core.exceptions import (
    PixlDiscardError,
    PixlOutOfHoursError,
    PixlRequeueMessageError,
    PixlStudyNotInPrimaryArchiveError,
)
from core.queue._base import PixlQueueInterface
from core.queue.models import AnonymisationMessage, ImagingRequestMessage, deserialise
from core.queue.producer import PixlProducer

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Self

    from aio_pika.abc import AbstractIncomingMessage
    from opentelemetry.context import Context
    from pika.adapters.blocking_connection import BlockingChannel
    from pika.spec import Basic, BasicProperties

    from core.token_buffer.tokens import TokenBucket

from loguru import logger


class PixlConsumer(PixlQueueInterface):
    """Connector to RabbitMQ. Consumes messages from a queue"""

    def __init__(
        self,
        queue_name: str,
        token_bucket: TokenBucket,
        token_bucket_key: str,
        callback: Callable[[ImagingRequestMessage], Awaitable[None]],
    ) -> None:
        """
        Creating connection to RabbitMQ queue
        :param token_bucket: Token bucket for the queue
        """
        super().__init__(queue_name=queue_name)
        self.token_bucket = token_bucket
        self.token_bucket_key = token_bucket_key
        self._callback: Callable[[ImagingRequestMessage], Awaitable[None]] = callback

    @property
    def _url(self) -> str:
        return f"amqp://{self._username}:{self._password}@{self._host}:{self._port}/"

    async def __aenter__(self) -> Self:
        """Establishes connection to queue."""
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        # Set number of messages in flight
        max_in_flight = config("PIXL_MAX_MESSAGES_IN_FLIGHT", cast=int)
        logger.info("Pika will consume up to {} messages concurrently", max_in_flight)
        await self._channel.set_qos(prefetch_count=max_in_flight)
        self._queue = await self._channel.declare_queue(
            self.queue_name,
            durable=True,
            arguments={"x-max-priority": 5},
        )
        return self

    async def _process_message(self, message: AbstractIncomingMessage) -> None:
        if not self.token_bucket.has_token(key=self.token_bucket_key):
            await asyncio.sleep(1)
            await message.reject(requeue=True)
            return

        pixl_message: ImagingRequestMessage = deserialise(message.body)
        logger.debug("Picked up from queue: {}", pixl_message.identifier)
        try:
            await self._callback(pixl_message)
        except PixlRequeueMessageError as requeue:
            logger.trace("Requeue message: {} from {}", pixl_message.identifier, requeue)
            await asyncio.sleep(1)
            await message.reject(requeue=True)
        except PixlStudyNotInPrimaryArchiveError as discard:
            logger.info(
                "Discard message: {} from {}. Sending to secondary imaging queue with priority {}.",
                pixl_message.identifier,
                discard,
                message.priority,
            )
            await asyncio.sleep(1)
            await message.reject(requeue=False)
            with PixlProducer(
                queue_name="imaging-secondary",
                host=config("RABBITMQ_HOST"),
                port=config("RABBITMQ_PORT", cast=int),
                username=config("RABBITMQ_USERNAME"),
                password=config("RABBITMQ_PASSWORD"),
            ) as producer:
                producer.publish([pixl_message], priority=message.priority)
        except PixlOutOfHoursError as nack_requeue:
            logger.trace(
                "Nack and requeue message: {} from {}", pixl_message.identifier, nack_requeue
            )
            await asyncio.sleep(10)
            await message.nack(requeue=True)
        except PixlDiscardError as exception:
            logger.warning("Failed message {}: {}", pixl_message.identifier, exception)
            await (
                message.ack()
            )  # ack so that we can see rate of message processing in rabbitmq admin
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to process {}. Not re-queuing message",
                pixl_message.identifier,
            )
            await (
                message.ack()
            )  # ack so that we can see rate of message processing in rabbitmq admin
        else:
            logger.success("Finished message {}", pixl_message.identifier)
            await message.ack()

    async def run(self) -> None:
        """Processes messages from queue asynchronously."""
        await self._queue.consume(self._process_message)

    async def __aexit__(self, *args: object, **kwargs: Any) -> None:
        """Requirement for the asynchronous context manager"""


class AnonymisationPixlConsumer(PixlQueueInterface):
    """Connector to RabbitMQ. Consumes messages from anonymisation queue"""

    def __init__(
        self,
        queue_name: str,
        callback: Callable[
            [AnonymisationMessage, Context | None, Callable[[], None], Callable[[], None]],
            None,
        ],
    ) -> None:
        """Creating connection to RabbitMQ queue"""
        super().__init__(queue_name=queue_name)
        self._callback: Callable[
            [AnonymisationMessage, Context | None, Callable[[], None], Callable[[], None]],
            None,
        ] = callback

    def __enter__(self) -> Self:
        """
        Establishes connection to queue.

        Unlike PixlConsumer (which uses aio_pika.connect_robust and so retries the
        initial connection automatically), pika's BlockingConnection has no built-in
        retry, so we configure one here. Without it, a transient failure to connect
        (e.g. RabbitMQ not quite ready yet at startup) kills the consumer thread
        permanently, since nothing else restarts it.
        """
        params = pika.ConnectionParameters(
            host=self._host,
            port=self._port,
            credentials=pika.PlainCredentials(self._username, self._password),
            connection_attempts=10,
            retry_delay=5,
        )
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()
        # Set number of messages in flight
        max_in_flight = config("PIXL_MAX_MESSAGES_IN_FLIGHT", cast=int)
        logger.info("Pika will consume up to {} messages concurrently", max_in_flight)
        self._channel.basic_qos(prefetch_count=max_in_flight)
        self._queue = self._channel.queue_declare(
            queue=self.queue_name,
            durable=True,
            arguments={"x-max-priority": 5},
        )
        return self

    def _process_message(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,  # noqa: ARG002
        body: bytes,
    ) -> None:
        pixl_message: AnonymisationMessage = deserialise(body)
        # PikaInstrumentor wraps this callback and extracts the trace context from the
        # message headers into the current context, so we just need to read it back here.
        parent_context = get_current()
        logger.debug("Picked up from queue: {}", pixl_message.identifier)
        try:
            # The callback settles the message later, from the pool thread, once
            # anonymisation finishes. Ack and nack hop back onto this connection.
            delivery_tag = method.delivery_tag
            self._callback(
                pixl_message,
                parent_context,
                partial(self.ack_message, delivery_tag),
                partial(self.nack_message, delivery_tag),
            )
        except PixlRequeueMessageError as requeue:
            logger.trace("Requeue message: {} from {}", pixl_message.identifier, requeue)
            time.sleep(1)
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
        except PixlOutOfHoursError as nack_requeue:
            logger.trace(
                "Nack and requeue message: {} from {}", pixl_message.identifier, nack_requeue
            )
            time.sleep(10)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        except PixlDiscardError as exception:
            logger.warning("Failed message {}: {}", pixl_message.identifier, exception)
            # ack so that we can see rate of message processing in rabbitmq admin
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to process {}. Not re-queuing message",
                pixl_message.identifier,
            )
            # ack so that we can see rate of message processing in rabbitmq admin
            channel.basic_ack(delivery_tag=method.delivery_tag)

    def ack_message(self, delivery_tag: int) -> None:
        """Ack from another thread by running the call on the connection thread."""

        def _ack() -> None:
            if self._channel is not None and self._channel.is_open:
                self._channel.basic_ack(delivery_tag=delivery_tag)

        self._connection.add_callback_threadsafe(_ack)

    def nack_message(self, delivery_tag: int) -> None:
        """Nack from another thread by running the call on the connection thread."""

        def _nack() -> None:
            if self._channel is not None and self._channel.is_open:
                self._channel.basic_nack(delivery_tag=delivery_tag, requeue=False)

        self._connection.add_callback_threadsafe(_nack)

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
