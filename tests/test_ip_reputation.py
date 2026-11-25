from ipaddress import ip_address

import pytest

from app.ip_reputation import HighRiskIPList


def test_high_risk_ip_list_matches_exact_addresses_and_cidrs() -> None:
    reputation = HighRiskIPList(
        [
            "203.0.113.8",
            "198.51.100.0/24",
            "2001:db8:abcd::/48",
        ]
    )

    assert reputation.is_high_risk("203.0.113.8")
    assert reputation.is_high_risk("198.51.100.27")
    assert reputation.is_high_risk(ip_address("2001:db8:abcd::4"))
    assert not reputation.is_high_risk("198.51.101.27")
    assert not reputation.is_high_risk("2001:db8:abce::4")


def test_high_risk_ip_list_accepts_empty_entries() -> None:
    assert not HighRiskIPList([]).is_high_risk("203.0.113.8")


def test_high_risk_ip_list_rejects_invalid_networks() -> None:
    with pytest.raises(ValueError):
        HighRiskIPList(["not-a-network"])


def test_high_risk_ip_list_rejects_invalid_addresses() -> None:
    reputation = HighRiskIPList(["203.0.113.0/24"])
    with pytest.raises(ValueError):
        reputation.is_high_risk("not-an-ip")
