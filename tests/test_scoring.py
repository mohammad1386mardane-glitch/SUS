import pytest
from pydantic import ValidationError

from app.rules import (
    BruteForceRule,
    HighRiskIPRule,
    ImpossibleTravelRule,
    NewDeviceAndCountryRule,
    UnusualHourRule,
)
from app.scoring import aggregate_score, score_to_decision
from app.settings import Settings


def test_aggregate_score_sums_triggered_rule_weights() -> None:
    score = aggregate_score((ImpossibleTravelRule(), NewDeviceAndCountryRule()))

    assert score == 70


def test_aggregate_score_caps_at_one_hundred() -> None:
    rules = (
        BruteForceRule(),
        HighRiskIPRule(),
        ImpossibleTravelRule(),
        NewDeviceAndCountryRule(),
        UnusualHourRule(),
    )

    assert aggregate_score(rules) == 100


def test_aggregate_score_is_zero_without_matching_rules() -> None:
    assert aggregate_score(()) == 0


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0, "allow"),
        (39, "allow"),
        (40, "challenge"),
        (78, "challenge"),
        (79, "deny"),
        (100, "deny"),
    ],
)
def test_score_to_decision_uses_inclusive_configured_boundaries(
    score: int,
    expected: str,
) -> None:
    assert score_to_decision(score, Settings()) == expected


def test_score_to_decision_uses_custom_thresholds() -> None:
    settings = Settings(allow_max_score=20, challenge_max_score=60)

    assert score_to_decision(20, settings) == "allow"
    assert score_to_decision(21, settings) == "challenge"
    assert score_to_decision(61, settings) == "deny"


@pytest.mark.parametrize("score", [-1, 101])
def test_score_to_decision_rejects_scores_outside_valid_range(score: int) -> None:
    with pytest.raises(ValueError, match="score must be between 0 and 100"):
        score_to_decision(score, Settings())


def test_score_to_decision_rejects_boolean_score() -> None:
    with pytest.raises(TypeError, match="score must be an integer"):
        score_to_decision(True, Settings())  # type: ignore[arg-type]


def test_settings_loads_thresholds_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOW_MAX_SCORE", "29")
    monkeypatch.setenv("CHALLENGE_MAX_SCORE", "69")

    settings = Settings(_env_file=None)

    assert settings.allow_max_score == 29
    assert settings.challenge_max_score == 69


def test_settings_rejects_invalid_threshold_order() -> None:
    with pytest.raises(ValidationError, match="score thresholds must satisfy"):
        Settings(allow_max_score=78, challenge_max_score=39)


def test_settings_validates_high_risk_ip_networks() -> None:
    settings = Settings(
        high_risk_ip_networks=["192.0.2.1", "2001:db8::/32"],
    )

    assert len(settings.high_risk_ip_networks) == 2
    with pytest.raises(ValidationError):
        Settings(high_risk_ip_networks=["not-an-ip-network"])
