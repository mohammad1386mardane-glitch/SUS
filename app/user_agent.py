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
