from datetime import datetime
from math import atan2, cos, isfinite, radians, sin, sqrt

from app.geoip import GeoIPResult

_EARTH_RADIUS_KM = 6371.0088


def required_travel_speed_kmh(
    previous_location: GeoIPResult | None,
    current_location: GeoIPResult | None,
    previous_timestamp: datetime,
    current_timestamp: datetime,
) -> float | None:
    if previous_location is None or current_location is None:
        return None

    previous_latitude = previous_location.latitude
    previous_longitude = previous_location.longitude
    current_latitude = current_location.latitude
    current_longitude = current_location.longitude
    if (
        previous_latitude is None
        or previous_longitude is None
        or current_latitude is None
        or current_longitude is None
    ):
        return None

    if not all(
        isfinite(value)
        for value in (
            previous_latitude,
            previous_longitude,
            current_latitude,
            current_longitude,
        )
    ):
        raise ValueError("coordinates must be finite")
    if not -90 <= previous_latitude <= 90 or not -90 <= current_latitude <= 90:
        raise ValueError("latitude must be between -90 and 90 degrees")
    if not -180 <= previous_longitude <= 180 or not -180 <= current_longitude <= 180:
        raise ValueError("longitude must be between -180 and 180 degrees")

    if (
        previous_timestamp.utcoffset() is None
        or current_timestamp.utcoffset() is None
    ):
        raise ValueError("timestamps must be timezone-aware")

    elapsed_seconds = (current_timestamp - previous_timestamp).total_seconds()
    if elapsed_seconds <= 0:
        raise ValueError("current_timestamp must be after previous_timestamp")

    distance_km = _distance_km(
        previous_latitude,
        previous_longitude,
        current_latitude,
        current_longitude,
    )
    return distance_km / (elapsed_seconds / 3600)


def _distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    latitude_a_radians = radians(latitude_a)
    latitude_b_radians = radians(latitude_b)
    latitude_delta = latitude_b_radians - latitude_a_radians
    longitude_delta = radians(longitude_b - longitude_a)

    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(latitude_a_radians)
        * cos(latitude_b_radians)
        * sin(longitude_delta / 2) ** 2
    )
    haversine = min(1.0, max(0.0, haversine))
    central_angle = 2 * atan2(sqrt(haversine), sqrt(1 - haversine))
    return _EARTH_RADIUS_KM * central_angle
