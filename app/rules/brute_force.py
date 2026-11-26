from dataclasses import dataclass

from app.rules.base import Rule, RuleContext

_MIN_CONSECUTIVE_FAILURES = 5
_MIN_DISTINCT_FAILED_IDENTITIES_PER_IP = 5


@dataclass(frozen=True, slots=True)
class BruteForceRule(Rule):
    name: str = "brute_force_or_credential_stuffing"
    weight: int = 60

    def condition(self, context: RuleContext) -> bool:
        return (
            context.consecutive_failures >= _MIN_CONSECUTIVE_FAILURES
            or self.credential_stuffing_detected(context)
        )

    def credential_stuffing_detected(self, context: RuleContext) -> bool:
        return (
            context.distinct_failed_users_per_ip
            >= _MIN_DISTINCT_FAILED_IDENTITIES_PER_IP
            and context.distinct_failed_devices_per_ip
            >= _MIN_DISTINCT_FAILED_IDENTITIES_PER_IP
        )

    def reasons(self, context: RuleContext) -> tuple[str, ...]:
        reasons: list[str] = []
        if context.consecutive_failures >= _MIN_CONSECUTIVE_FAILURES:
            reasons.append(self.name)
        if self.credential_stuffing_detected(context):
            reasons.append("credential_stuffing_multiple_users_and_devices")
        return tuple(reasons)
