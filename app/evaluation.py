from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import LoginEvent
from app.db.repositories import LoginEventRepository, UserProfileRepository
from app.features import (
    detect_new_login_signals,
    required_travel_speed_kmh,
    time_of_day_deviation_hours,
)
from app.geoip import GeoIPResult, lookup_ip
from app.ip_reputation import HighRiskIPList
from app.ml_inference import InferenceService
from app.rules import (
    BruteForceRule,
    HighRiskIPRule,
    ImpossibleTravelRule,
    NewDeviceAndCountryRule,
    RuleContext,
    RuleRegistry,
    UnusualHourRule,
    UserAgentProfileChangeRule,
)
from app.schemas import LoginEventRequest, LoginEventResponse
from app.scoring import aggregate_score, blend_scores, score_to_decision
from app.settings import Settings
from app.user_agent import suspicious_user_agent_profile_change

_RULES = RuleRegistry(
    (
        ImpossibleTravelRule(),
        BruteForceRule(),
        NewDeviceAndCountryRule(),
        HighRiskIPRule(),
        UnusualHourRule(),
        UserAgentProfileChangeRule(),
    )
)


def evaluate_and_store(
    event: LoginEventRequest,
    session: Session,
    settings: Settings,
) -> LoginEventResponse:
    event_timestamp = event.timestamp.astimezone(UTC)
    event_ip = str(event.ip)
    event_repository = LoginEventRepository(session)
    profile_repository = UserProfileRepository(session)
    previous_events = event_repository.list_for_user_before(
        event.user_id,
        event_timestamp,
        limit=4,
    )
    previous_event = previous_events[0] if previous_events else None

    current_location = (
        lookup_ip(event_ip, db_path=settings.geoip_db_path)
        if settings.geoip_enabled
        else None
    )
    previous_location = (
        _geo_result_from_json(previous_event.geo)
        if previous_event is not None
        else None
    )
    travel_speed = (
        required_travel_speed_kmh(
            previous_location,
            current_location,
            _as_utc(previous_event.timestamp),
            event_timestamp,
        )
        if previous_event is not None
        else None
    )

    profile = profile_repository.get_by_user_id(event.user_id)
    login_signals = detect_new_login_signals(
        event.device_id,
        current_location.country if current_location is not None else None,
        profile,
    )
    previous_same_device = next(
        (
            previous
            for previous in previous_events
            if previous.device_id == event.device_id
            and _is_trusted_login(
                previous.success,
                previous.decision,
                previous.reasons,
            )
        ),
        None,
    )
    suspicious_user_agent_change = (
        suspicious_user_agent_profile_change(
            event.user_agent,
            previous_same_device.user_agent,
        )
        if previous_same_device is not None
        else False
    )
    time_deviation = time_of_day_deviation_hours(event_timestamp, profile)
    consecutive_failures = _consecutive_failures(event.success, previous_events)
    window_start = event_timestamp - timedelta(
        seconds=settings.credential_stuffing_window_seconds
    )
    recent_users = event_repository.distinct_users_for_ip_between(
        event_ip,
        window_start,
        event_timestamp,
    )
    recent_users.add(event.user_id)
    failed_user_device_pairs = event_repository.failed_user_device_pairs_for_ip_between(
        event_ip,
        window_start,
        event_timestamp,
    )
    if not event.success:
        failed_user_device_pairs.add((event.user_id, event.device_id))
    failed_users = {user_id for user_id, _ in failed_user_device_pairs}
    failed_devices = {device_id for _, device_id in failed_user_device_pairs}
    high_risk_ip_list = HighRiskIPList(settings.high_risk_ip_networks)

    context = RuleContext(
        impossible_travel_speed_kmh=travel_speed,
        consecutive_failures=consecutive_failures,
        distinct_users_per_ip=len(recent_users),
        distinct_failed_users_per_ip=len(failed_users),
        distinct_failed_devices_per_ip=len(failed_devices),
        suspicious_user_agent_profile_change=suspicious_user_agent_change,
        is_new_device=login_signals.is_new_device,
        is_new_country=login_signals.is_new_country,
        is_high_risk_ip=high_risk_ip_list.is_high_risk(event_ip),
        time_deviation_hours=time_deviation,
    )
    matched_rules = _RULES.evaluate(context)
    rule_score = aggregate_score(matched_rules)
    reasons: list[str] = []
    for rule in matched_rules:
        if isinstance(rule, BruteForceRule):
            reasons.extend(rule.reasons(context))
        else:
            reasons.append(rule.name)
    score = rule_score
    if settings.ml_enabled:
        ml_result = InferenceService(settings.model_path).score(context)
        score = blend_scores(rule_score, ml_result.risk_score)
        if ml_result.is_anomaly:
            reasons.append("ml_anomaly")
    decision = score_to_decision(score, settings)
    event_id = f"evt_{uuid4().hex}"
    response = LoginEventResponse(
        event_id=event_id,
        risk_score=score,
        decision=decision,
        reasons=reasons,
    )

    geo = _geo_to_json(current_location)
    event_repository.add(
        LoginEvent(
            event_id=event_id,
            user_id=event.user_id,
            ip=event_ip,
            geo=geo,
            device_id=event.device_id,
            user_agent=event.user_agent,
            timestamp=event_timestamp,
            success=event.success,
            risk_score=score,
            decision=decision,
            reasons=reasons,
        )
    )
    if _is_trusted_login(event.success, decision, reasons):
        profile_repository.add_trusted_login(
            user_id=event.user_id,
            device_id=event.device_id,
            country=current_location.country if current_location is not None else None,
            hour=event_timestamp.hour,
        )
    session.commit()
    return response


def _is_trusted_login(
    success: bool,
    decision: str | None,
    reasons: list[str],
) -> bool:
    return (
        success
        and decision == "allow"
        and all(reason == "new_device_and_country" for reason in reasons)
    )


def _consecutive_failures(
    current_success: bool,
    previous_events: list[LoginEvent],
) -> int:
    if current_success:
        return 0

    count = 1
    for previous_event in previous_events:
        if previous_event.success:
            break
        count += 1
    return count


def _as_utc(value: datetime) -> datetime:
    if value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _geo_result_from_json(geo: dict[str, Any] | None) -> GeoIPResult | None:
    if geo is None:
        return None

    country = geo.get("country")
    city = geo.get("city")
    latitude = geo.get("latitude")
    longitude = geo.get("longitude")
    if country is not None and not isinstance(country, str):
        raise ValueError("stored GeoIP country must be a string or null")
    if city is not None and not isinstance(city, str):
        raise ValueError("stored GeoIP city must be a string or null")
    if not _is_optional_number(latitude) or not _is_optional_number(longitude):
        raise ValueError("stored GeoIP coordinates must be numbers or null")

    return GeoIPResult(
        country=country,
        city=city,
        latitude=float(latitude) if latitude is not None else None,
        longitude=float(longitude) if longitude is not None else None,
    )


def _is_optional_number(value: object) -> bool:
    return value is None or (
        isinstance(value, (int, float)) and not isinstance(value, bool)
    )


def _geo_to_json(location: GeoIPResult | None) -> dict[str, Any] | None:
    if location is None:
        return None
    return {
        "country": location.country,
        "city": location.city,
        "latitude": location.latitude,
        "longitude": location.longitude,
    }
