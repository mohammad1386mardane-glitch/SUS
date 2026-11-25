import pytest

from app.user_agent import UserAgentFeatures, parse_user_agent


@pytest.mark.parametrize(
    ("user_agent", "expected"),
    [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 "
            "Safari/537.36",
            UserAgentFeatures("Chrome", "Windows", "desktop"),
        ),
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
            "Mobile/15E148 Safari/604.1",
            UserAgentFeatures("Mobile Safari", "iOS", "mobile"),
        ),
        (
            "Mozilla/5.0 (iPad; CPU OS 13_2_3 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 "
            "Mobile/15E148 Safari/604.1",
            UserAgentFeatures("Mobile Safari", "iOS", "tablet"),
        ),
        (
            "Googlebot/2.1 (+http://www.google.com/bot.html)",
            UserAgentFeatures("Googlebot", "Other", "bot"),
        ),
        (
            "UnknownClient",
            UserAgentFeatures("Other", "Other", "other"),
        ),
    ],
)
def test_parse_user_agent_extracts_browser_os_and_device_type(
    user_agent: str,
    expected: UserAgentFeatures,
) -> None:
    assert parse_user_agent(user_agent) == expected


@pytest.mark.parametrize("user_agent", ["", "  \t"])
def test_parse_user_agent_rejects_empty_input(user_agent: str) -> None:
    with pytest.raises(ValueError, match="user_agent cannot be empty"):
        parse_user_agent(user_agent)
