import token_bucket as tb


def create_token_bucket(_rate=5, _capacity=5):
    """ Creates a token bucket for rate limitation

    Uses the token bucket implementation from `Flaconry <https://github.com/falconry/token-bucket>` to limit access
    rates for downloading images from PACS/VNA. During discussion with the UCLH imaging team, the optimal rate limit
    was determined as 5 images per second for now. However, there might be still situations where this is too much which
    is why _rate and _capacity have been provided as parameters so that they can change.

    :param _rate: the number of tokens added per second
    :param _capacity: the maximum number of tokens in the bucket at any one point in time

    :returns: a Limiter object
    """
    return tb.Limiter(rate=_rate, capacity=_capacity, storage=tb.MemoryStorage())


def get_token(token_bucket: tb.Limiter):
    """ Attempts to retrieve token from exising bucket.

    Rate limitation is governed by the existence of tokens in a bucket, whereby the bucket is refilled every second. As
    long as a token can be retrieved, an image can be downloaded from PACS/VNA. Should there be no more tokens inside
    the bucket, the image request is added back into the queue.
    Note that the Limiter object can operate the rate on different "streams", which are specified by a string object,
    also called key. This key has been hard coded here to "pixl" as we do not expect more than one streams at this point
    in time.

    :param token_bucket: the token bucket that limits the rate for the download and which has been created beforehand
    :returns: True if a token could be removed, otherwise false
    """
    return token_bucket.consume("pixl")
