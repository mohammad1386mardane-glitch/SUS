from dataclasses import dataclass

import pytest

from app.rules import (
    BruteForceRule,
    HighRiskIPRule,
    ImpossibleTravelRule,
    NewDeviceAndCountryRule,
    Rule,
    RuleContext,
    RuleRegistry,
    UnusualHourRule,
    UserAgentProfileChangeRule,
)


@dataclass(frozen=True, slots=True)
class FlagRule(Rule):
    flag_name: str

    def condition(self, context: RuleContext) -> bool:
        return bool(getattr(context, self.flag_name))


def test_registry_returns_matching_rules_in_registration_order() -> None:
    rules = (
        FlagRule("new_device", 20, "is_new_device"),
        FlagRule("high_risk_ip", 30, "is_high_risk_ip"),
        FlagRule("new_country", 25, "is_new_country"),
    )
    registry = RuleRegistry(rules)

    matches = registry.evaluate(RuleContext(is_new_device=True, is_high_risk_ip=True))

    assert matches == (rules[0], rules[1])


def test_registry_returns_no_matches_when_context_has_no_signals() -> None:
    registry = RuleRegistry(
        (
            BruteForceRule(),
            HighRiskIPRule(),
            ImpossibleTravelRule(),
            NewDeviceAndCountryRule(),
            UnusualHourRule(),
        )
    )

    assert registry.evaluate(RuleContext()) == ()


def test_registry_rejects_duplicate_rule_names() -> None:
    with pytest.raises(ValueError, match="rule names must be unique"):
        RuleRegistry(
            (
                FlagRule("same_name", 10, "is_new_device"),
                FlagRule("same_name", 20, "is_new_country"),
            )
        )


@pytest.mark.parametrize("name", ["", "  "])
def test_rule_rejects_empty_name(name: str) -> None:
    with pytest.raises(ValueError, match="rule name cannot be empty"):
        FlagRule(name, 10, "is_new_device")


@pytest.mark.parametrize("weight", [-1, 101])
def test_rule_rejects_weight_outside_score_range(weight: int) -> None:
    with pytest.raises(ValueError, match="rule weight must be between 0 and 100"):
        FlagRule("test_rule", weight, "is_new_device")


def test_rule_rejects_non_integer_weight() -> None:
    with pytest.raises(TypeError, match="rule weight must be an integer"):
        FlagRule("test_rule", 1.5, "is_new_device")  # type: ignore[arg-type]


@pytest.mark.parametrize("weight", [0, 100])
def test_rule_accepts_weight_boundaries(weight: int) -> None:
    assert FlagRule("test_rule", weight, "is_new_device").weight == weight


@pytest.mark.parametrize(
    ("speed", "expected"),
    [(None, False), (900, False), (900.01, True), (1200, True)],
)
def test_impossible_travel_rule_uses_strict_speed_threshold(
    speed: float | None,
    expected: bool,
) -> None:
    rule = ImpossibleTravelRule()

    assert rule.condition(RuleContext(impossible_travel_speed_kmh=speed)) is expected


@pytest.mark.parametrize(
    (
        "consecutive_failures",
        "distinct_failed_users_per_ip",
        "distinct_failed_devices_per_ip",
        "expected",
    ),
    [
        (0, 0, 0, False),
        (4, 4, 4, False),
        (5, 0, 0, True),
        (0, 5, 4, False),
        (0, 4, 5, False),
        (0, 5, 5, True),
    ],
)
def test_brute_force_rule_requires_both_shared_ip_diversity_signals(
    consecutive_failures: int,
    distinct_failed_users_per_ip: int,
    distinct_failed_devices_per_ip: int,
    expected: bool,
) -> None:
    rule = BruteForceRule()

    assert (
        rule.condition(
            RuleContext(
                consecutive_failures=consecutive_failures,
                distinct_failed_users_per_ip=distinct_failed_users_per_ip,
                distinct_failed_devices_per_ip=distinct_failed_devices_per_ip,
            )
        )
        is expected
    )


def test_brute_force_rule_reports_both_signals() -> None:
    rule = BruteForceRule()
    context = RuleContext(
        consecutive_failures=5,
        distinct_failed_users_per_ip=5,
        distinct_failed_devices_per_ip=5,
    )

    assert rule.reasons(context) == (
        "brute_force_or_credential_stuffing",
        "credential_stuffing_multiple_users_and_devices",
    )


@pytest.mark.parametrize(
    ("is_new_device", "suspicious_change", "expected"),
    [
        (False, False, False),
        (False, True, True),
        (True, True, False),
    ],
)
def test_user_agent_change_rule_avoids_new_device_double_counting(
    is_new_device: bool,
    suspicious_change: bool,
    expected: bool,
) -> None:
    rule = UserAgentProfileChangeRule()

    assert (
        rule.condition(
            RuleContext(
                is_new_device=is_new_device,
                suspicious_user_agent_profile_change=suspicious_change,
            )
        )
        is expected
    )


@pytest.mark.parametrize(
    ("is_new_device", "is_new_country", "expected"),
    [
        (False, False, False),
        (True, False, False),
        (False, True, False),
        (True, True, True),
    ],
)
def test_new_device_country_rule_requires_both_signals(
    is_new_device: bool,
    is_new_country: bool,
    expected: bool,
) -> None:
    rule = NewDeviceAndCountryRule()

    assert (
        rule.condition(
            RuleContext(
                is_new_device=is_new_device,
                is_new_country=is_new_country,
            )
        )
        is expected
    )


@pytest.mark.parametrize(
    ("is_high_risk_ip", "expected"), [(False, False), (True, True)]
)
def test_high_risk_ip_rule_uses_reputation_signal(
    is_high_risk_ip: bool,
    expected: bool,
) -> None:
    rule = HighRiskIPRule()

    assert rule.condition(RuleContext(is_high_risk_ip=is_high_risk_ip)) is expected


@pytest.mark.parametrize(
    ("time_deviation_hours", "expected"),
    [(None, False), (5, False), (6, True), (12, True)],
)
def test_unusual_hour_rule_uses_deviation_threshold(
    time_deviation_hours: int | None,
    expected: bool,
) -> None:
    rule = UnusualHourRule()

    assert (
        rule.condition(RuleContext(time_deviation_hours=time_deviation_hours))
        is expected
    )
