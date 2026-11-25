from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address, ip_address
from pathlib import Path

from geoip2.database import Reader
from geoip2.errors import AddressNotFoundError

from app.settings import get_settings


@dataclass(frozen=True, slots=True)
class GeoIPResult:
    country: str | None
    city: str | None
    latitude: float | None
    longitude: float | None


def lookup_ip(
    ip: str | IPv4Address | IPv6Address,
    *,
    db_path: Path | None = None,
) -> GeoIPResult | None:
    address = str(ip_address(ip))
    database_path = db_path or get_settings().geoip_db_path

    with Reader(str(database_path)) as reader:
        try:
            response = reader.city(address)
        except AddressNotFoundError:
            return None

    location = response.location
    return GeoIPResult(
        country=response.country.iso_code,
        city=response.city.name,
        latitude=location.latitude,
        longitude=location.longitude,
    )
