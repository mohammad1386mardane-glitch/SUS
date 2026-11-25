from collections.abc import Iterable

from app.rules.base import Rule
from app.schemas import Decision
from app.settings import Settings

RULE_SCORE_WEIGHT = 0.6
ML_SCORE_WEIGHT = 0.4


def aggregate_score(matched_rules: Iterable[Rule]) -> int:
    return min(sum(rule.weight for rule in matched_rules), 100)


def blend_scores(rule_score: int, ml_score: int) -> int:
    for name, score in (("rule_score", rule_score), ("ml_score", ml_score)):
        if isinstance(score, bool) or not isinstance(score, int):
            raise TypeError(f"{name} must be an integer")
        if not 0 <= score <= 100:
            raise ValueError(f"{name} must be between 0 and 100")

    return round(
        RULE_SCORE_WEIGHT * rule_score + ML_SCORE_WEIGHT * ml_score,
    )


def score_to_decision(score: int, settings: Settings) -> Decision:
    if isinstance(score, bool) or not isinstance(score, int):
        raise TypeError("score must be an integer")
    if not 0 <= score <= 100:
        raise ValueError("score must be between 0 and 100")

    if score <= settings.allow_max_score:
        return "allow"
    if score <= settings.challenge_max_score:
        return "challenge"
    return "deny"
