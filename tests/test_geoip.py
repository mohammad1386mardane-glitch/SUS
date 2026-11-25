from pathlib import Path
from types import SimpleNamespace

import pytest

import app.geoip as geoip


class FakeReader:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self.address: str | None = None
        self.exit_info: tuple[object, object, object] | None = None

    def __enter__(self) -> "FakeReader":
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.exit_info = (exc_type, exc_value, traceback)

    def city(self, address: str) -> SimpleNamespace:
        self.address = address
        return SimpleNamespace(
            country=SimpleNamespace(iso_code="US"),
            city=SimpleNamespace(name="Example City"),
            location=SimpleNamespace(latitude=37.386, longitude=-122.0838),
        )


def test_lookup_ip_returns_city_record_and_closes_reader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    readers: list[FakeReader] = []

    def create_reader(database_path: str) -> FakeReader:
        reader = FakeReader(database_path)
        readers.append(reader)
        return reader

    monkeypatch.setattr(geoip, "Reader", create_reader)
    result = geoip.lookup_ip("203.0.113.5", db_path=tmp_path / "GeoLite2-City.mmdb")

    assert result == geoip.GeoIPResult(
        country="US",
        city="Example City",
        latitude=37.386,
        longitude=-122.0838,
    )
    assert readers[0].database_path == str(tmp_path / "GeoLite2-City.mmdb")
    assert readers[0].address == "203.0.113.5"
    assert readers[0].exit_info == (None, None, None)


def test_lookup_ip_rejects_invalid_addresses_before_opening_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_opened(database_path: str) -> FakeReader:
        raise AssertionError(f"database should not open: {database_path}")

    monkeypatch.setattr(geoip, "Reader", fail_if_opened)

    with pytest.raises(ValueError):
        geoip.lookup_ip("not-an-ip")


def test_lookup_ip_returns_none_when_address_is_not_in_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readers: list[FakeReader] = []

    class MissingRecordReader(FakeReader):
        def city(self, address: str) -> SimpleNamespace:
            self.address = address
            raise geoip.AddressNotFoundError(
                "No matching address record",
                ip_address=address,
            )

    def create_reader(database_path: str) -> FakeReader:
        reader = MissingRecordReader(database_path)
        readers.append(reader)
        return reader

    monkeypatch.setattr(geoip, "Reader", create_reader)

    assert geoip.lookup_ip("203.0.113.5") is None
    assert readers[0].exit_info == (None, None, None)


def test_lookup_ip_surfaces_database_open_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_to_open(database_path: str) -> FakeReader:
        raise FileNotFoundError(database_path)

    monkeypatch.setattr(geoip, "Reader", fail_to_open)

    with pytest.raises(FileNotFoundError):
        geoip.lookup_ip("203.0.113.5")
