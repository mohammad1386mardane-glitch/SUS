import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from secrets import token_urlsafe

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.db.models import LoginEvent, UserProfile
from app.db.repositories import LoginEventRepository, UserProfileRepository
from app.db.session import get_session
from app.geoip import GeoIPResult
from app.main import app
from app.ml_data import write_synthetic_dataset
from app.ml_inference import InferenceResult, InferenceService
from app.ml_training import train_isolation_forest
from app.rules.base import RuleContext
from app.settings import Settings, get_settings


@pytest.fixture
def api_key() -> str:
    return token_urlsafe(32)


@pytest.fixture
def client(api_key: str, db_session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_key=SecretStr(api_key),
        ml_enabled=False,
    )

    def override_get_session() -> Iterator[Session]:
        with Session(db_session.get_bind(), expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
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


def test_demo_page_is_available(client: TestClient) -> None:
    response = client.get("/demo")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Login Risk Test Console" in response.text


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


def test_evaluate_returns_scored_response(
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


def test_evaluate_blends_ml_score_and_persists_anomaly_reason(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_score(
        service: InferenceService,
        context: RuleContext,
    ) -> InferenceResult:
        return InferenceResult(
            risk_score=75,
            is_anomaly=True,
            decision_function=-0.1,
            model_version=1,
        )

    monkeypatch.setattr(InferenceService, "score", fake_score)
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_key=SecretStr(api_key),
        ml_enabled=True,
    )

    response = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json()["risk_score"] == 30
    assert response.json()["decision"] == "allow"
    assert response.json()["reasons"] == ["ml_anomaly"]
    db_session.expire_all()
    stored = LoginEventRepository(db_session).list_for_user("u1")
    assert stored[0].risk_score == 30
    assert stored[0].reasons == ["ml_anomaly"]


def test_evaluate_with_registered_model_returns_bounded_blended_score(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    tmp_path: Path,
) -> None:
    training_data = tmp_path / "training.csv"
    model_base_path = tmp_path / "model.joblib"
    write_synthetic_dataset(
        training_data,
        normal_count=100,
        suspicious_count=30,
        seed=31,
    )
    train_isolation_forest(training_data, model_base_path, random_state=31)
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_key=SecretStr(api_key),
        ml_enabled=True,
        model_path=model_base_path,
    )

    response = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    response_data = response.json()
    assert 0 <= response_data["risk_score"] <= 40
    assert response_data["decision"] in {"allow", "challenge"}
    assert response_data["reasons"] in ([], ["ml_anomaly"])


def test_evaluate_scores_and_stores_consecutive_failed_attempts(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
) -> None:
    repository = LoginEventRepository(db_session)
    timestamp = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    for minutes_ago in range(1, 5):
        repository.add(
            LoginEvent(
                user_id="u1",
                ip="203.0.113.5",
                device_id="d1",
                user_agent="browser",
                timestamp=timestamp - timedelta(minutes=minutes_ago),
                success=False,
                reasons=[],
            )
        )
    db_session.commit()
    failed_event = {**login_event, "success": False}

    response = client.post(
        "/v1/login-events/evaluate",
        json=failed_event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json()["risk_score"] == 60
    assert response.json()["decision"] == "challenge"
    assert response.json()["reasons"] == ["brute_force_or_credential_stuffing"]
    db_session.expire_all()
    stored_events = LoginEventRepository(db_session).list_for_user("u1")
    assert len(stored_events) == 5
    assert stored_events[0].risk_score == 60


def test_evaluate_counts_distinct_users_within_five_minute_window(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
) -> None:
    repository = LoginEventRepository(db_session)
    timestamp = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    history = (
        (4, "user-2"),
        (3, "user-3"),
        (2, "user-4"),
        (1, "user-5"),
        (6, "expired-user"),
    )
    for minutes_ago, user_id in history:
        repository.add(
            LoginEvent(
                user_id=user_id,
                ip="203.0.113.5",
                device_id="d1",
                user_agent="browser",
                timestamp=timestamp - timedelta(minutes=minutes_ago),
                success=True,
                reasons=[],
            )
        )
    db_session.commit()

    response = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json()["risk_score"] == 60
    assert response.json()["reasons"] == ["brute_force_or_credential_stuffing"]


def test_successful_login_resets_consecutive_failure_rule(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
) -> None:
    repository = LoginEventRepository(db_session)
    timestamp = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    for minutes_ago in range(1, 5):
        repository.add(
            LoginEvent(
                user_id="u1",
                ip="203.0.113.5",
                device_id="d1",
                user_agent="browser",
                timestamp=timestamp - timedelta(minutes=minutes_ago),
                success=False,
                reasons=[],
            )
        )
    db_session.commit()

    response = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json()["risk_score"] == 0
    assert response.json()["reasons"] == []


def test_evaluate_uses_configured_high_risk_ip_network(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_key=SecretStr(api_key),
        high_risk_ip_networks=["203.0.113.0/24"],
    )

    response = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json()["risk_score"] == 40
    assert response.json()["decision"] == "challenge"
    assert response.json()["reasons"] == ["high_risk_ip"]


def test_evaluate_uses_geoip_and_profile_for_travel_and_novelty_rules(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_time = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    LoginEventRepository(db_session).add(
        LoginEvent(
            user_id="u1",
            ip="198.51.100.10",
            geo={
                "country": "US",
                "city": "Example",
                "latitude": 0.0,
                "longitude": 0.0,
            },
            device_id="old-device",
            user_agent="browser",
            timestamp=event_time - timedelta(hours=1),
            success=True,
            reasons=[],
        )
    )
    UserProfileRepository(db_session).save(
        UserProfile(
            user_id="u1",
            usual_countries=["US"],
            usual_devices=["old-device"],
            usual_hours=[12],
        )
    )
    db_session.commit()

    def fake_lookup_ip(ip: object, *, db_path: Path | None = None) -> GeoIPResult:
        assert str(ip) == "203.0.113.5"
        assert db_path == Path("data/GeoLite2-City.mmdb")
        return GeoIPResult("GB", "Example", 0.0, 10.0)

    monkeypatch.setattr("app.evaluation.lookup_ip", fake_lookup_ip)
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_key=SecretStr(api_key),
        geoip_enabled=True,
    )

    response = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json()["risk_score"] == 70
    assert response.json()["decision"] == "challenge"
    assert response.json()["reasons"] == [
        "impossible_travel",
        "new_device_and_country",
    ]


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


def test_evaluate_rejects_naive_timestamp(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
) -> None:
    naive_event = {**login_event, "timestamp": "2026-11-25T12:00:00"}

    response = client.post(
        "/v1/login-events/evaluate",
        json=naive_event,
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
