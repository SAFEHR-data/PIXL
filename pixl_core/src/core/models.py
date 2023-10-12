from pydantic import BaseModel
from dataclasses import dataclass
from .token_buffer import TokenBucket


@dataclass
class AppState:
    token_bucket = TokenBucket(rate=0, capacity=5)


class TokenRefreshUpdate(BaseModel):
    rate: float
