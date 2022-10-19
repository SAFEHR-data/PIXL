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

import time

from token_buffer import tokens


def test_token_bucket_created() -> None:
    """Checks whether token bucket can be created."""
    assert tokens.create_token_bucket() is not None


def test_retrieve_token() -> None:
    """Checks whether token can be retrieved from created token bucket."""
    assert tokens.get_token(tokens.create_token_bucket()) is True


def test_refill_tokens() -> None:
    """Checks whether the refill happens after one second for a bucket size of 1."""
    test_tb = tokens.create_token_bucket(_rate=1, _capacity=1)
    assert tokens.get_token(test_tb) is True
    assert tokens.get_token(test_tb) is False
    time.sleep(1)
    assert tokens.get_token(test_tb) is True
