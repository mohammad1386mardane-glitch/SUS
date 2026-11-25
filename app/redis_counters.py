from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from hashlib import sha256
from uuid import uuid4

from redis import Redis

from app.settings import get_settings

_RECORD_FAILURE = """
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', '(' .. ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[4])
return 1
"""

_GET_FAILURE_COUNTS = """
local now = tonumber(ARGV[1])
return {
    redis.call('ZCOUNT', KEYS[1], now - 60, now),
    redis.call('ZCOUNT', KEYS[1], now - 300, now),
    redis.call('ZCOUNT', KEYS[1], now - 3600, now)
}
"""

_INCREMENT_WITH_TTL = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""

_VELOCITY_TTL_SECONDS = 3600


@lru_cache
def get_redis_client() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


@dataclass(frozen=True, slots=True)
class FailedAttemptVelocityCounts:
    last_1_minute: int
    last_5_minutes: int
    last_60_minutes: int


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
        user_hash = _hashed_user_id(user_id)
        return f"{self.key_prefix}:{window_seconds}:{user_hash}"


class FailedAttemptVelocity:
    """Stores failed attempts and reads rolling 1, 5, and 60 minute counts."""

    def __init__(
        self,
        client: Redis,
        *,
        key_prefix: str = "login:failed:velocity",
    ) -> None:
        if not key_prefix:
            raise ValueError("key_prefix cannot be empty")
        self.client = client
        self.key_prefix = key_prefix

    def record_failure(
        self,
        user_id: str,
        *,
        occurred_at: datetime | None = None,
    ) -> None:
        key = self._key(user_id)
        timestamp = _timestamp(occurred_at or datetime.now(UTC))
        member = f"{timestamp:.6f}:{uuid4().hex}"
        self.client.eval(
            _RECORD_FAILURE,
            1,
            key,
            timestamp,
            member,
            timestamp - _VELOCITY_TTL_SECONDS,
            _VELOCITY_TTL_SECONDS,
        )

    def get_counts(
        self,
        user_id: str,
        *,
        now: datetime | None = None,
    ) -> FailedAttemptVelocityCounts:
        key = self._key(user_id)
        timestamp = _timestamp(now or datetime.now(UTC))
        result = self.client.eval(
            _GET_FAILURE_COUNTS,
            1,
            key,
            timestamp,
        )
        return FailedAttemptVelocityCounts(
            last_1_minute=int(result[0]),
            last_5_minutes=int(result[1]),
            last_60_minutes=int(result[2]),
        )

    def _key(self, user_id: str) -> str:
        return f"{self.key_prefix}:{_hashed_user_id(user_id)}"


def _hashed_user_id(user_id: str) -> str:
    if not user_id:
        raise ValueError("user_id cannot be empty")
    return sha256(user_id.encode("utf-8")).hexdigest()


def _timestamp(value: datetime) -> float:
    if value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.timestamp()
