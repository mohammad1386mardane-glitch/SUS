from dataclasses import dataclass

from app.rules.base import Rule, RuleContext


@dataclass(frozen=True, slots=True)
class UserAgentProfileChangeRule(Rule):
    name: str = "user_agent_profile_change"
    weight: int = 15

    def condition(self, context: RuleContext) -> bool:
        return (
            context.suspicious_user_agent_profile_change
            and not context.is_new_device
        )
