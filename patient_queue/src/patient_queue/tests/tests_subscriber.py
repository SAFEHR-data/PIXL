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
from token_buffer.tokens import TokenBucket
from patient_queue.subscriber import PixlConsumer


def test_create() -> None:
    """Checks that PIXL producer can be instantiated."""
    pc = PixlConsumer(queue="test", port=5672, user="rabbit_user", password="rabbit_pw", token_bucket=TokenBucket())
    assert True

