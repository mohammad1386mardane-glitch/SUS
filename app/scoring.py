from collections.abc import Iterable

from app.rules.base import Rule
from app.schemas import Decision
from app.settings import Settings


def aggregate_score(matched_rules: Iterable[Rule]) -> int:
    return min(sum(rule.weight for rule in matched_rules), 100)


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
