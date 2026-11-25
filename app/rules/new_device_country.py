from dataclasses import dataclass

from app.rules.base import Rule, RuleContext


@dataclass(frozen=True, slots=True)
class NewDeviceAndCountryRule(Rule):
    name: str = "new_device_and_country"
    weight: int = 30

    def condition(self, context: RuleContext) -> bool:
        return context.is_new_device and context.is_new_country
