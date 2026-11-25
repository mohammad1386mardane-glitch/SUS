from dataclasses import dataclass
from hashlib import sha256

from redis import Redis

_INCREMENT_WITH_WINDOW = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {count, redis.call('TTL', KEYS[1])}
"""


@dataclass(frozen=True, slots=True)
class RateLimitWindow:
    request_count: int
    retry_after_seconds: int


class ApiKeyRateLimiter:
    def __init__(
        self,
        client: Redis,
        *,
        key_prefix: str = "api:rate-limit",
    ) -> None:
        if not key_prefix:
            raise ValueError("key_prefix cannot be empty")
        self.client = client
        self.key_prefix = key_prefix

    def consume(self, api_key: str, *, window_seconds: int) -> RateLimitWindow:
        if not api_key:
            raise ValueError("api_key cannot be empty")
        if window_seconds < 1:
            raise ValueError("window_seconds must be greater than zero")

        key_hash = sha256(api_key.encode("utf-8")).hexdigest()
        result = self.client.eval(
            _INCREMENT_WITH_WINDOW,
            1,
            f"{self.key_prefix}:{window_seconds}:{key_hash}",
            window_seconds,
        )
        if not isinstance(result, (list, tuple)) or len(result) != 2:
            raise RuntimeError("Redis returned an invalid rate-limit result")
        request_count, retry_after_seconds = (int(value) for value in result)
        if request_count < 1 or retry_after_seconds < 0:
            raise RuntimeError("Redis returned invalid rate-limit values")
        return RateLimitWindow(
            request_count=request_count,
            retry_after_seconds=max(retry_after_seconds, 1),
        )
