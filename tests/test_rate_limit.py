import fakeredis
import pytest

from app.rate_limit import ApiKeyRateLimiter


@pytest.fixture
def redis_client() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis(decode_responses=True)


def test_rate_limiter_counts_by_hashed_api_key_and_sets_expiry(
    redis_client: fakeredis.FakeRedis,
) -> None:
    limiter = ApiKeyRateLimiter(redis_client)

    first = limiter.consume("secret-api-key-one", window_seconds=60)
    second = limiter.consume("secret-api-key-one", window_seconds=60)
    other_key = limiter.consume("secret-api-key-two", window_seconds=60)

    assert first.request_count == 1
    assert second.request_count == 2
    assert other_key.request_count == 1
    assert 1 <= second.retry_after_seconds <= 60
    redis_key = next(redis_client.scan_iter(match="api:rate-limit:*"))
    assert "secret-api-key" not in redis_key
    assert redis_client.ttl(redis_key) > 0


@pytest.mark.parametrize(
    ("api_key", "window_seconds"),
    [("", 60), ("secret-api-key", 0), ("secret-api-key", -1)],
)
def test_rate_limiter_rejects_invalid_input(
    redis_client: fakeredis.FakeRedis,
    api_key: str,
    window_seconds: int,
) -> None:
    limiter = ApiKeyRateLimiter(redis_client)

    with pytest.raises(ValueError):
        limiter.consume(api_key, window_seconds=window_seconds)
