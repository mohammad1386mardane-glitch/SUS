from dataclasses import dataclass

from app.rules.base import Rule, RuleContext


@dataclass(frozen=True, slots=True)
class HighRiskIPRule(Rule):
    name: str = "high_risk_ip"
    weight: int = 40

    def condition(self, context: RuleContext) -> bool:
        return context.is_high_risk_ip
