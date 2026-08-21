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
from __future__ import annotations

from unittest.mock import Mock

import pytest

from core.anon_queue.subscriber import AnonymisationPixlConsumer

TEST_QUEUE = "test_anon_consume"


class ExpectedTestError(Exception):
    """Expected error for testing."""


@pytest.mark.usefixtures("run_containers")
def test_run() -> None:
    """Checks that the consumer starts consuming messages."""
    callback = Mock()

    with AnonymisationPixlConsumer(
        queue_name=TEST_QUEUE,
        callback=callback,
    ) as consumer:
        consumer._channel.basic_consume = Mock()
        consumer._channel.start_consuming = Mock()

        consumer.run()

        consumer._channel.basic_consume.assert_called_once_with(
            queue=TEST_QUEUE,
            on_message_callback=consumer._process_message,
            auto_ack=False,
        )
        consumer._channel.start_consuming.assert_called_once()


@pytest.mark.usefixtures("run_containers")
def test_process_message(mock_anon_message) -> None:
    """Checks that a received message is passed to the callback."""
    callback = Mock()

    with AnonymisationPixlConsumer(
        queue_name=TEST_QUEUE,
        callback=callback,
    ) as consumer:
        message = Mock()
        message.body = mock_anon_message.serialise()

        consumer._process_message(message)

        callback.assert_called_once_with(mock_anon_message)
