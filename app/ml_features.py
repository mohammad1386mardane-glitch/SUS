from math import isfinite

from app.rules.base import RuleContext

FEATURE_NAMES = (
    "travel_speed_ratio",
    "consecutive_failures_ratio",
    "distinct_users_per_ip_ratio",
    "is_new_device",
    "is_new_country",
    "is_high_risk_ip",
    "time_deviation_ratio",
)


def features_from_context(context: RuleContext) -> dict[str, float]:
    return {
        "travel_speed_ratio": _ratio(context.impossible_travel_speed_kmh, 1800),
        "consecutive_failures_ratio": _ratio(context.consecutive_failures, 10),
        "distinct_users_per_ip_ratio": _ratio(context.distinct_users_per_ip, 10),
        "is_new_device": float(context.is_new_device),
        "is_new_country": float(context.is_new_country),
        "is_high_risk_ip": float(context.is_high_risk_ip),
        "time_deviation_ratio": _ratio(context.time_deviation_hours, 12),
    }


def _ratio(value: int | float | None, maximum: int) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool) or not isfinite(value) or value < 0:
        raise ValueError("model feature values must be finite and non-negative")
    return min(float(value) / maximum, 1.0)
