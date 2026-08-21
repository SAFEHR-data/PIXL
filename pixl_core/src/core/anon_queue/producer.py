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
    from core.anon_queue.message import AnonymisationMessage

tracer = trace.get_tracer("pixl_core.anon_queue.producer")


class AnonymisationProducer(PixlBlockingInterface):
    """Anonymisation publisher for RabbitMQ"""

    def publish(self, messages: list[AnonymisationMessage]) -> None:
        """
        Sends a list of serialised messages to a queue.
        :param messages: list of messages to be sent to queue
        """
        if len(messages) == 0:
            logger.warning("List of messages is empty so nothing will be published to queue.")
            return

        logger.info("Publishing {} messages to queue: {}", len(messages), self.queue_name)
        for msg in messages:
            attributes = {
                "project_name": msg.project_name,
                "resource_ids": msg.resource_ids,
                "series_uids": msg.series_uids,
                "study_uids": msg.study_uids,
            }
            with tracer.start_as_current_span("publish_message", attributes=attributes):
                self._publish_message(msg)

    def _publish_message(self, message: AnonymisationMessage) -> None:
        """
        Publish a single serialised message to a queue.
        :param message: message to be sent to queue
        """
        serialised_msg = message.serialise()
        self._channel.basic_publish(
            exchange="",
            routing_key=self.queue_name,
            body=serialised_msg,
            properties=BasicProperties(
                delivery_mode=DeliveryMode.Persistent,
            ),
        )

        logger.bind(
            project_name=message.project_name,
            resource_id=message.resource_ids,
            series_uid=message.series_uids,
            study_uid=message.study_uids,
        ).debug(
            "AnonymisationMessage {} published to queue {}",
            message,
            self.queue_name,
        )

    def clear_queue(self) -> None:
        """
        Triggering a purge of all the messages currently in the queue. Mainly used to
        clean after tests.
        """
        self._channel.queue_purge(queue=self.queue_name)
