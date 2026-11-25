from functools import lru_cache
from hashlib import sha256

from redis import Redis

from app.settings import get_settings

_INCREMENT_WITH_TTL = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


@lru_cache
def get_redis_client() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


class FailedAttemptCounter:
    """Counts failed attempts in fixed windows starting with the first failure."""

    def __init__(
        self,
        client: Redis,
        *,
        key_prefix: str = "login:failed",
    ) -> None:
        if not key_prefix:
            raise ValueError("key_prefix cannot be empty")
        self.client = client
        self.key_prefix = key_prefix

    def increment(self, user_id: str, *, window_seconds: int = 3600) -> int:
        key = self._key(user_id, window_seconds)
        count = self.client.eval(
            _INCREMENT_WITH_TTL,
            1,
            key,
            window_seconds,
        )
        return int(count)

    def get_count(self, user_id: str, *, window_seconds: int = 3600) -> int:
        key = self._key(user_id, window_seconds)
        count = self.client.get(key)
        return int(count) if count is not None else 0

    def _key(self, user_id: str, window_seconds: int) -> str:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        if window_seconds < 1:
            raise ValueError("window_seconds must be greater than zero")
        user_hash = sha256(user_id.encode("utf-8")).hexdigest()
        return f"{self.key_prefix}:{window_seconds}:{user_hash}"
