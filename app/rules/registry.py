from collections.abc import Iterable

from app.rules.base import Rule, RuleContext


class RuleRegistry:
    def __init__(self, rules: Iterable[Rule]) -> None:
        self._rules = tuple(rules)
        names = [rule.name for rule in self._rules]
        if len(names) != len(set(names)):
            raise ValueError("rule names must be unique")

    def evaluate(self, context: RuleContext) -> tuple[Rule, ...]:
        return tuple(rule for rule in self._rules if rule.condition(context))
