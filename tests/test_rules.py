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
    ("consecutive_failures", "distinct_users_per_ip", "expected"),
    [
        (0, 0, False),
        (4, 4, False),
        (5, 0, True),
        (0, 5, True),
        (5, 5, True),
    ],
)
def test_brute_force_rule_triggers_on_either_threshold(
    consecutive_failures: int,
    distinct_users_per_ip: int,
    expected: bool,
) -> None:
    rule = BruteForceRule()

    assert (
        rule.condition(
            RuleContext(
                consecutive_failures=consecutive_failures,
                distinct_users_per_ip=distinct_users_per_ip,
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
