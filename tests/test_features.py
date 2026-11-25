from datetime import UTC, datetime, timedelta

import pytest

from app.features import required_travel_speed_kmh
from app.geoip import GeoIPResult


def location(latitude: float | None, longitude: float | None) -> GeoIPResult:
    return GeoIPResult(
        country="US",
        city="Example City",
        latitude=latitude,
        longitude=longitude,
    )


def test_required_travel_speed_uses_haversine_distance() -> None:
    previous = datetime(2026, 1, 1, tzinfo=UTC)
    current = previous + timedelta(hours=1)

    speed = required_travel_speed_kmh(
        location(0, 0),
        location(0, 1),
        previous,
        current,
    )

    assert speed == pytest.approx(111.195, abs=0.01)


def test_required_travel_speed_takes_short_path_across_dateline() -> None:
    previous = datetime(2026, 1, 1, tzinfo=UTC)
    current = previous + timedelta(hours=1)

    speed = required_travel_speed_kmh(
        location(0, 179.5),
        location(0, -179.5),
        previous,
        current,
    )

    assert speed == pytest.approx(111.195, abs=0.01)


def test_required_travel_speed_returns_none_without_coordinates() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)

    assert (
        required_travel_speed_kmh(
            None,
            location(0, 1),
            timestamp,
            timestamp + timedelta(hours=1),
        )
        is None
    )
    assert (
        required_travel_speed_kmh(
            location(None, None),
            location(0, 1),
            timestamp,
            timestamp + timedelta(hours=1),
        )
        is None
    )


@pytest.mark.parametrize(
    ("previous_timestamp", "current_timestamp", "message"),
    [
        (
            datetime(2026, 1, 1),
            datetime(2026, 1, 1, 1),
            "timestamps must be timezone-aware",
        ),
        (
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 1, tzinfo=UTC),
            "current_timestamp must be after previous_timestamp",
        ),
        (
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2025, 12, 31, tzinfo=UTC),
            "current_timestamp must be after previous_timestamp",
        ),
    ],
)
def test_required_travel_speed_rejects_invalid_timestamps(
    previous_timestamp: datetime,
    current_timestamp: datetime,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        required_travel_speed_kmh(
            location(0, 0),
            location(0, 1),
            previous_timestamp,
            current_timestamp,
        )


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(91, 0), (0, 181), (float("inf"), 0)],
)
def test_required_travel_speed_rejects_invalid_coordinates(
    latitude: float,
    longitude: float,
) -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(ValueError):
        required_travel_speed_kmh(
            location(latitude, longitude),
            location(0, 1),
            timestamp,
            timestamp + timedelta(hours=1),
        )
