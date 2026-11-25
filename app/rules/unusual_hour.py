from dataclasses import dataclass

from app.rules.base import Rule, RuleContext

_UNUSUAL_HOUR_THRESHOLD = 6


@dataclass(frozen=True, slots=True)
class UnusualHourRule(Rule):
    name: str = "unusual_hour"
    weight: int = 15

    def condition(self, context: RuleContext) -> bool:
        deviation = context.time_deviation_hours
        return deviation is not None and deviation >= _UNUSUAL_HOUR_THRESHOLD
