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
from time import sleep
from typing import List

from patient_queue._base import PixlBlockingInterface

LOGGER = logging.getLogger(__name__)


class PixlProducer(PixlBlockingInterface):
    """Generic publisher for RabbitMQ"""

    def publish(self, messages: List[bytes]) -> None:
        """
        Sends a list of serialised messages to a queue.
        :param messages: list of messages to be sent to queue
        """
        LOGGER.debug(f"Publishing {len(messages)} messages to queue: {self.queue_name}")
        if len(messages) > 0:
            for msg in messages:
                LOGGER.debug("Preparing to publish")
                self._channel.basic_publish(
                    exchange="", routing_key=self.queue_name, body=msg
                )
                # RabbitMQ can miss-order messages if there is not a sufficient delay
                sleep(0.1)
                LOGGER.debug(
                    f"Message {msg.decode()} published to queue {self.queue_name}"
                )
        else:
            LOGGER.debug(
                "List of messages is empty so nothing will be published to queue."
            )

    def clear_queue(self) -> None:
        """Triggering a purge of all the messages currently in the queue. Mainly used to
        clean after tests."""
        self._channel.queue_purge(queue=self.queue_name)
