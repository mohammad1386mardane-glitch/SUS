import fakeredis
import pytest

from app.redis_counters import FailedAttemptCounter


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
