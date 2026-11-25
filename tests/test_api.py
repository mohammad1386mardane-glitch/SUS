import json
import logging
from collections.abc import Iterator
from secrets import token_urlsafe

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.main import app
from app.settings import Settings, get_settings


@pytest.fixture
def api_key() -> str:
    return token_urlsafe(32)


@pytest.fixture
def client(api_key: str) -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_key=SecretStr(api_key)
    )
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def login_event() -> dict[str, object]:
    return {
        "user_id": "u1",
        "ip": "203.0.113.5",
        "user_agent": "browser",
        "device_id": "d1",
        "timestamp": "2026-11-25T12:00:00Z",
        "success": True,
    }


def test_health_is_public(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_evaluate_requires_api_key(
    client: TestClient,
    login_event: dict[str, object],
) -> None:
    assert client.post("/v1/login-events/evaluate", json=login_event).status_code == 401
    assert (
        client.post(
            "/v1/login-events/evaluate",
            json=login_event,
            headers={"X-API-Key": token_urlsafe(32)},
        ).status_code
        == 401
    )


def test_evaluate_returns_stub_response(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
) -> None:
    response = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["event_id"].startswith("evt_")
    assert len(response_data["event_id"]) == 36
    assert response_data["risk_score"] == 0
    assert response_data["decision"] == "allow"
    assert response_data["reasons"] == []


def test_evaluate_fails_closed_without_configured_api_key(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(api_key=SecretStr(""))

    response = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 503


def test_evaluate_rejects_invalid_event(
    client: TestClient,
    api_key: str,
) -> None:
    response = client.post(
        "/v1/login-events/evaluate",
        json={"ip": "not-an-ip"},
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 422


def test_request_logs_are_json_and_response_has_request_id(
    client: TestClient,
    api_key: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="app.request")
    response = client.post(
        "/v1/login-events/evaluate",
        json={
            "user_id": "u1",
            "ip": "203.0.113.5",
            "user_agent": "browser",
            "device_id": "d1",
            "timestamp": "2026-11-25T12:00:00Z",
            "success": True,
        },
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 32
    log_entry = json.loads(caplog.records[-1].getMessage())
    assert log_entry["request_id"] == request_id
    assert log_entry["method"] == "POST"
    assert log_entry["path"] == "/v1/login-events/evaluate"
    assert log_entry["status_code"] == 200
    assert isinstance(log_entry["duration_ms"], float)
    assert api_key not in caplog.records[-1].getMessage()
