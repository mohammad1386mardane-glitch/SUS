from dataclasses import dataclass

from app.rules.base import Rule, RuleContext

_MIN_CONSECUTIVE_FAILURES = 5
_MIN_DISTINCT_USERS_PER_IP = 5


@dataclass(frozen=True, slots=True)
class BruteForceRule(Rule):
    name: str = "brute_force_or_credential_stuffing"
    weight: int = 60

    def condition(self, context: RuleContext) -> bool:
        return (
            context.consecutive_failures >= _MIN_CONSECUTIVE_FAILURES
            or context.distinct_users_per_ip >= _MIN_DISTINCT_USERS_PER_IP
        )
