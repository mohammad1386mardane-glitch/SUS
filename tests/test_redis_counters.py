from datetime import UTC, datetime, timedelta

import fakeredis
import pytest

from app.redis_counters import (
    FailedAttemptCounter,
    FailedAttemptVelocity,
    FailedAttemptVelocityCounts,
)


@pytest.fixture
def redis_client() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis(decode_responses=True)


def test_failed_attempt_count_has_per_user_window_and_ttl(
    redis_client: fakeredis.FakeRedis,
) -> None:
    counter = FailedAttemptCounter(redis_client)

    assert counter.increment("user-one", window_seconds=60) == 1
    key = next(redis_client.scan_iter(match="login:failed:*"))
    assert "user-one" not in key
    first_ttl = redis_client.ttl(key)
    assert first_ttl > 0

    assert counter.increment("user-one", window_seconds=60) == 2
    assert redis_client.ttl(key) <= first_ttl
    assert counter.increment("user-two", window_seconds=60) == 1
    assert counter.increment("user-one", window_seconds=300) == 1
    assert counter.get_count("user-one", window_seconds=60) == 2
    assert counter.get_count("user-one", window_seconds=300) == 1


@pytest.mark.parametrize(
    ("user_id", "window_seconds"),
    [("", 60), ("user-one", 0), ("user-one", -1)],
)
def test_failed_attempt_count_rejects_invalid_input(
    redis_client: fakeredis.FakeRedis,
    user_id: str,
    window_seconds: int,
) -> None:
    counter = FailedAttemptCounter(redis_client)

    with pytest.raises(ValueError):
        counter.increment(user_id, window_seconds=window_seconds)


def test_failed_attempt_velocity_counts_rolling_windows_inclusively(
    redis_client: fakeredis.FakeRedis,
) -> None:
    velocity = FailedAttemptVelocity(redis_client)
    now = datetime(2026, 11, 25, 12, tzinfo=UTC)

    for seconds_ago in (3601, 3600, 300, 60, 0):
        velocity.record_failure(
            "user-one",
            occurred_at=now - timedelta(seconds=seconds_ago),
        )

    assert velocity.get_counts("user-one", now=now) == FailedAttemptVelocityCounts(
        last_1_minute=2,
        last_5_minutes=3,
        last_60_minutes=4,
    )
    assert velocity.get_counts("user-two", now=now) == FailedAttemptVelocityCounts(
        last_1_minute=0,
        last_5_minutes=0,
        last_60_minutes=0,
    )
    key = next(redis_client.scan_iter(match="login:failed:velocity:*"))
    assert "user-one" not in key
    assert redis_client.zcard(key) == 4
    assert redis_client.ttl(key) > 0


def test_failed_attempt_velocity_preserves_same_timestamp_events(
    redis_client: fakeredis.FakeRedis,
) -> None:
    velocity = FailedAttemptVelocity(redis_client)
    now = datetime(2026, 11, 25, 12, tzinfo=UTC)

    velocity.record_failure("user-one", occurred_at=now)
    velocity.record_failure("user-one", occurred_at=now)

    assert velocity.get_counts("user-one", now=now).last_1_minute == 2


@pytest.mark.parametrize(
    ("user_id", "timestamp"),
    [
        ("", datetime(2026, 11, 25, tzinfo=UTC)),
        ("user-one", datetime(2026, 11, 25)),
    ],
)
def test_failed_attempt_velocity_rejects_invalid_input(
    redis_client: fakeredis.FakeRedis,
    user_id: str,
    timestamp: datetime,
) -> None:
    velocity = FailedAttemptVelocity(redis_client)

    with pytest.raises(ValueError):
        velocity.record_failure(user_id, occurred_at=timestamp)
