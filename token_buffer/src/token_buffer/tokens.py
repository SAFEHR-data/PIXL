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

import token_bucket as tb


def create_token_bucket(_rate: int = 5, _capacity: int = 5) -> tb.Limiter:
    """Creates a token bucket for rate limitation

    Uses the token bucket implementation from `Flaconry`
    <https://github.com/falconry/token-bucket> to limit access rates for downloading
    images from PACS/VNA. During discussion with the UCLH imaging team, the optimal
    rate limit was determined as 5 images per second for now. However, there might be
    still situations where this is too much which is why _rate and _capacity have been
    provided as parameters so that they can change.

    :param _rate: the number of tokens added per second
    :param _capacity: the maximum number of tokens in the bucket at any one point in
                      time

    :returns: a Limiter object
    """
    return tb.Limiter(rate=_rate, capacity=_capacity, storage=tb.MemoryStorage())


def get_token(token_bucket: tb.Limiter) -> bool:
    """Attempts to retrieve token from exising bucket.

    Rate limitation is governed by the existence of tokens in a bucket, whereby the
    bucket is refilled every second. As long as a token can be retrieved, an image can
    be downloaded from PACS/VNA. Should there be no more tokens inside the bucket, the
    image request is added back into the queue. Note that the Limiter object can operate
    the rate on different "streams", which are specified by a string object, also called
    key. This key has been hard coded here to "pixl" as we do not expect more than one
    streams at this point in time.

    :param token_bucket: the token bucket that limits the rate for the download and
    which has been created beforehand :returns: True if a token could be removed,
    otherwise false
    """
    return bool(token_bucket.consume("pixl"))
