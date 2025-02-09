# noqa: D100
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

import typing

import token_bucket as tb


class TokenBucket(tb.Limiter):
    """
    Rate limitation is governed by the existence of tokens in a bucket, whereby the
    bucket is refilled every second. As long as a token can be retrieved, an item can
    be downloaded. Should there be no more tokens inside the bucket, the request is
    added back into the queue.

    Note that the Limiter object can operate the rate on
    different "streams", which are specified by a string object, also called key. This
    key has been hard coded here to accept one of two values: 'primary' or 'secondary',
    representing two different streams.
    """

    _keys: typing.ClassVar = ["primary", "secondary"]

    def __init__(
        self,
        rate: float = 5,
        capacity: int = 5,
    ) -> None:
        """
        Uses the token bucket implementation from `Falconry`
        <https://github.com/falconry/token-bucket> to limit access rates for downloading
        /extracting images where throttling is required.

        :param rate: The number of tokens added per second
        :param capacity: The maximum number of tokens in the bucket at any point in time
        :param storage: Type of storage used to hold the tokens
        """
        self._zero_rate = False

        if rate == 0:
            rate = 1  # tb.Limiter does not allow zero rates, so keep track...
            self._zero_rate = True

        super().__init__(rate=rate, capacity=capacity, storage=tb.MemoryStorage())

    def has_token(self, key: str) -> bool:
        """Does this token bucket have a token for the given key?"""
        if key not in self._keys:
            message = f"Key must be one of {self._keys}, not '{key}'"
            raise ValueError(message)
        return not self._zero_rate and bool(self.consume(key))

    @property
    def rate(self) -> float:
        """Rate in items per second"""
        return 0 if self._zero_rate else float(self._rate)

    @rate.setter
    def rate(self, value: float) -> None:
        if not isinstance(value, float):
            msg = "Cannot set the rate with a non integer value"
            raise TypeError(msg)

        if value == 0:
            self._zero_rate = True
        else:
            self._zero_rate = False
            self._rate = value
