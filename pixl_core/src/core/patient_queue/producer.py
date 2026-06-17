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
"""Producer for RabbitMQ"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from opentelemetry import trace
from pika import BasicProperties, DeliveryMode

from ._base import PixlBlockingInterface

if TYPE_CHECKING:
    from core.patient_queue.message import Message

tracer = trace.get_tracer("pixl_core.patient_queue.producer")


class PixlProducer(PixlBlockingInterface):
    """Generic publisher for RabbitMQ"""

    def publish(self, messages: list[Message], priority: int) -> None:
        """
        Sends a list of serialised messages to a queue.
        :param messages: list of messages to be sent to queue
        :param priority: priority of the messages, from 1 (lowest) to 5 (highest)
        """
        if len(messages) == 0:
            logger.warning("List of messages is empty so nothing will be published to queue.")
            return

        logger.info("Publishing {} messages to queue: {}", len(messages), self.queue_name)
        for msg in messages:
            attributes = {
                "project_name": msg.project_name,
                "mrn": msg.mrn,
                "accession_number": msg.accession_number,
                "study_uid": msg.study_uid,
            }
            with tracer.start_as_current_span("publish_message", attributes=attributes):
                self._publish_message(msg, priority)

    def _publish_message(self, message: Message, priority: int) -> None:
        """
        Publish a single serialised message to a queue.
        :param message: message to be sent to queue
        :param priority: priority of the message, from 1 (lowest) to 5 (highest)
        """
        serialised_msg = message.serialise()
        self._channel.basic_publish(
            exchange="",
            routing_key=self.queue_name,
            body=serialised_msg,
            properties=BasicProperties(
                delivery_mode=DeliveryMode.Persistent,
                priority=priority,
            ),
        )

        logger.bind(
            project_name=message.project_name,
            mrn=message.mrn,
            accession_number=message.accession_number,
            study_uid=message.study_uid,
        ).debug(
            "Message {} published to queue {} with priority {}",
            message,
            self.queue_name,
            priority,
        )

    def clear_queue(self) -> None:
        """
        Triggering a purge of all the messages currently in the queue. Mainly used to
        clean after tests.
        """
        self._channel.queue_purge(queue=self.queue_name)
