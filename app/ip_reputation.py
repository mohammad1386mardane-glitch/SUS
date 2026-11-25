from collections.abc import Iterable
from ipaddress import IPv4Address, IPv6Address, ip_address, ip_network


class HighRiskIPList:
    def __init__(self, networks: Iterable[str]) -> None:
        self._networks = tuple(
            ip_network(network, strict=False) for network in networks
        )

    def is_high_risk(self, ip: str | IPv4Address | IPv6Address) -> bool:
        address = ip_address(ip)
        return any(address in network for network in self._networks)
