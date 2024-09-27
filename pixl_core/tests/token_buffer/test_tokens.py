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

import time

from core.token_buffer import TokenBucket


def test_retrieve_token() -> None:
    """Checks whether token can be retrieved from created token bucket."""
    bucket = TokenBucket()
    assert bucket.has_token(key="primary")
    assert bucket.has_token(key="secondary")


def test_refill_tokens() -> None:
    """Checks whether the refill happens after one second for a bucket size of 1."""
    bucket = TokenBucket(rate=1, capacity=1)

    assert bucket.has_token(key="primary")
    # Interrogating the bucket within 1 second we find that it's empty
    assert bucket.has_token(key="primary") is False

    # but will be refilled after 1 second
    time.sleep(1)
    assert bucket.has_token(key="primary")


def test_zero_rate() -> None:
    """Test that the refill rate can be set to zero"""
    assert TokenBucket(rate=0).rate == 0


def test_non_integer_rates_allowed() -> None:
    """Test that non-integer rates can be used"""
    assert _is_close(TokenBucket(rate=0.5).rate, 0.5)


def _is_close(a: float, b: float) -> bool:
    return abs(a - b) < 1e-10
