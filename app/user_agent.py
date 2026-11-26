from dataclasses import dataclass
from typing import Literal, Protocol, cast

from user_agents import parse

DeviceType = Literal["bot", "tablet", "mobile", "desktop", "other"]


class _Family(Protocol):
    @property
    def family(self) -> str: ...


class _ParsedUserAgent(Protocol):
    @property
    def browser(self) -> _Family: ...

    @property
    def os(self) -> _Family: ...

    @property
    def is_bot(self) -> bool: ...

    @property
    def is_tablet(self) -> bool: ...

    @property
    def is_mobile(self) -> bool: ...

    @property
    def is_pc(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class UserAgentFeatures:
    browser: str
    operating_system: str
    device_type: DeviceType


def parse_user_agent(user_agent: str) -> UserAgentFeatures:
    normalized_user_agent = user_agent.strip()
    if not normalized_user_agent:
        raise ValueError("user_agent cannot be empty")

    parsed = cast(_ParsedUserAgent, parse(normalized_user_agent))
    if parsed.is_bot:
        device_type: DeviceType = "bot"
    elif parsed.is_tablet:
        device_type = "tablet"
    elif parsed.is_mobile:
        device_type = "mobile"
    elif parsed.is_pc:
        device_type = "desktop"
    else:
        device_type = "other"

    return UserAgentFeatures(
        browser=parsed.browser.family,
        operating_system=parsed.os.family,
        device_type=device_type,
    )


def suspicious_user_agent_profile_change(
    current_user_agent: str,
    previous_user_agent: str,
) -> bool:
    if not current_user_agent.strip() or not previous_user_agent.strip():
        return False

    current = parse_user_agent(current_user_agent)
    previous = parse_user_agent(previous_user_agent)
    changed_dimensions = (
        current.browser != previous.browser
        and current.browser != "Other"
        and previous.browser != "Other",
        current.operating_system != previous.operating_system
        and current.operating_system != "Other"
        and previous.operating_system != "Other",
        current.device_type != previous.device_type
        and current.device_type != "other"
        and previous.device_type != "other",
    )
    return sum(changed_dimensions) >= 2
