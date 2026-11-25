from dataclasses import dataclass

from app.rules.base import Rule, RuleContext

_IMPOSSIBLE_TRAVEL_THRESHOLD_KMH = 900


@dataclass(frozen=True, slots=True)
class ImpossibleTravelRule(Rule):
    name: str = "impossible_travel"
    weight: int = 40

    def condition(self, context: RuleContext) -> bool:
        speed = context.impossible_travel_speed_kmh
        return speed is not None and speed > _IMPOSSIBLE_TRAVEL_THRESHOLD_KMH
