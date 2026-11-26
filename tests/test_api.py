import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from secrets import token_urlsafe

import fakeredis
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.orm import Session

from app.db.models import LoginEvent, LoginFeedback, UserProfile
from app.db.repositories import (
    LoginEventRepository,
    LoginFeedbackRepository,
    UserProfileRepository,
)
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


def test_openapi_includes_examples_for_public_schemas() -> None:
    schemas = app.openapi()["components"]["schemas"]

    assert schemas["LoginEventRequest"]["examples"][0]["ip"] == "203.0.113.42"
    assert schemas["FeedbackRequest"]["examples"][0]["label"] == "real_attack"
    assert schemas["LoginEventResponse"]["examples"][0]["risk_score"] == 0
    assert (
        schemas["RiskHistoryResponse"]["examples"][0]["events"][0]["decision"]
        == "allow"
    )
    assert schemas["HealthResponse"]["examples"] == [{"status": "ok"}]


def test_prometheus_endpoint_exposes_request_latency_and_decisions(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
) -> None:
    evaluation = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": api_key},
    )
    metrics = client.get("/metrics")

    assert evaluation.status_code == 200
    assert metrics.status_code == 200
    assert metrics.headers["content-type"].startswith("text/plain")
    assert (
        'sus_http_requests_total{method="POST",path="/v1/login-events/evaluate",'
        'status_code="200"}'
    ) in metrics.text
    assert (
        'sus_http_request_duration_seconds_count{method="POST",'
        'path="/v1/login-events/evaluate"}'
    ) in metrics.text
    assert 'sus_login_decisions_total{decision="allow"}' in metrics.text


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


@pytest.mark.parametrize(
    ("user_agent", "device_id", "expected_score", "expected_reasons"),
    [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "d1",
            0,
            [],
        ),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
            "Gecko/20100101 Firefox/121.0",
            "d1",
            0,
            [],
        ),
        (
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) "
            "Gecko/20100101 Firefox/121.0",
            "d1",
            15,
            ["user_agent_profile_change"],
        ),
        ("not-a-recognized-user-agent", "d1", 0, []),
        (
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) "
            "Gecko/20100101 Firefox/121.0",
            "new-device",
            0,
            [],
        ),
    ],
)
def test_evaluate_scores_only_multi_dimension_changes_for_known_device(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
    user_agent: str,
    device_id: str,
    expected_score: int,
    expected_reasons: list[str],
) -> None:
    db_session.add(
        LoginEvent(
            user_id="u1",
            ip="203.0.113.5",
            device_id="d1",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            timestamp=datetime(2026, 11, 25, 11, 59, tzinfo=UTC),
            success=True,
            risk_score=0,
            decision="allow",
            reasons=[],
        )
    )
    db_session.add(UserProfile(user_id="u1", usual_devices=["d1"]))
    db_session.commit()
    current_event = {
        **login_event,
        "user_agent": user_agent,
        "device_id": device_id,
    }

    response = client.post(
        "/v1/login-events/evaluate",
        json=current_event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json()["risk_score"] == expected_score
    assert response.json()["reasons"] == expected_reasons


@pytest.mark.parametrize(
    ("success", "decision", "risk_score", "reasons"),
    [
        (False, "challenge", 60, ["brute_force_or_credential_stuffing"]),
        (True, "challenge", 40, ["high_risk_ip"]),
        (True, "deny", 80, ["impossible_travel", "high_risk_ip"]),
        (True, "allow", 15, ["user_agent_profile_change"]),
    ],
)
def test_untrusted_events_do_not_reset_trusted_user_agent_baseline(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
    success: bool,
    decision: str,
    risk_score: int,
    reasons: list[str],
) -> None:
    trusted_user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    changed_user_agent = (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"
    )
    db_session.add(
        LoginEvent(
            user_id="u1",
            ip="203.0.113.5",
            device_id="d1",
            user_agent=trusted_user_agent,
            timestamp=datetime(2026, 11, 25, 11, 58, tzinfo=UTC),
            success=True,
            risk_score=0,
            decision="allow",
            reasons=[],
        )
    )
    db_session.add(
        LoginEvent(
            user_id="u1",
            ip="203.0.113.5",
            device_id="d1",
            user_agent=changed_user_agent,
            timestamp=datetime(2026, 11, 25, 11, 59, tzinfo=UTC),
            success=success,
            risk_score=risk_score,
            decision=decision,
            reasons=reasons,
        )
    )
    db_session.add(UserProfile(user_id="u1", usual_devices=["d1"]))
    db_session.commit()
    current_event = {**login_event, "user_agent": changed_user_agent}

    response = client.post(
        "/v1/login-events/evaluate",
        json=current_event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json()["risk_score"] == 15
    assert response.json()["reasons"] == ["user_agent_profile_change"]


def test_evaluate_rejects_missing_or_blank_user_agent(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
) -> None:
    missing_user_agent = dict(login_event)
    missing_user_agent.pop("user_agent")
    blank_user_agent = {**login_event, "user_agent": "  \t"}

    for event in (missing_user_agent, blank_user_agent):
        response = client.post(
            "/v1/login-events/evaluate",
            json=event,
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 422


def test_user_agent_change_does_not_double_count_new_device_country_signal(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_session.add(
        LoginEvent(
            user_id="u1",
            ip="203.0.113.5",
            device_id="d1",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            timestamp=datetime(2026, 11, 25, 11, 59, tzinfo=UTC),
            success=True,
            risk_score=0,
            decision="allow",
            reasons=[],
        )
    )
    db_session.add(
        UserProfile(
            user_id="u1",
            usual_devices=[],
            usual_countries=["CA"],
        )
    )
    db_session.commit()

    def fake_lookup_ip(ip: object, *, db_path: Path | None = None) -> GeoIPResult:
        return GeoIPResult("US", "Example", 0.0, 0.0)

    monkeypatch.setattr("app.evaluation.lookup_ip", fake_lookup_ip)
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_key=SecretStr(api_key),
        geoip_enabled=True,
    )
    event = {
        **login_event,
        "user_agent": (
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) "
            "Gecko/20100101 Firefox/121.0"
        ),
    }

    response = client.post(
        "/v1/login-events/evaluate",
        json=event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json()["risk_score"] == 30
    assert response.json()["reasons"] == ["new_device_and_country"]


def test_feedback_persists_once_for_an_evaluated_event(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
) -> None:
    evaluation = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": api_key},
    )
    event_id = evaluation.json()["event_id"]

    feedback = client.post(
        "/v1/feedback",
        json={"event_id": event_id, "label": "real_attack"},
        headers={"X-API-Key": api_key},
    )

    assert feedback.status_code == 201
    assert feedback.json() == {"event_id": event_id, "label": "real_attack"}
    stored_event = LoginEventRepository(db_session).get_by_event_id(event_id)
    assert stored_event is not None
    stored_feedback = LoginFeedbackRepository(db_session).get_for_login_event(
        stored_event.id
    )
    assert isinstance(stored_feedback, LoginFeedback)
    assert stored_feedback.label == "real_attack"

    duplicate = client.post(
        "/v1/feedback",
        json={"event_id": event_id, "label": "false_positive"},
        headers={"X-API-Key": api_key},
    )

    assert duplicate.status_code == 409


def test_feedback_requires_api_key(client: TestClient) -> None:
    response = client.post(
        "/v1/feedback",
        json={"event_id": f"evt_{'0' * 32}", "label": "false_positive"},
    )

    assert response.status_code == 401


def test_feedback_rejects_unknown_events_and_invalid_labels(
    client: TestClient,
    api_key: str,
) -> None:
    unknown_event = client.post(
        "/v1/feedback",
        json={"event_id": f"evt_{'0' * 32}", "label": "false_positive"},
        headers={"X-API-Key": api_key},
    )
    invalid_label = client.post(
        "/v1/feedback",
        json={"event_id": f"evt_{'1' * 32}", "label": "maybe"},
        headers={"X-API-Key": api_key},
    )

    assert unknown_event.status_code == 404
    assert invalid_label.status_code == 422


def test_risk_history_is_authenticated_paginated_and_privacy_limited(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="app.request")
    event_ids: list[str] = []
    user_id = "private-user-987"
    for hour in (12, 13, 14):
        response = client.post(
            "/v1/login-events/evaluate",
            json={
                **login_event,
                "user_id": user_id,
                "timestamp": f"2026-11-25T{hour:02d}:00:00Z",
            },
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200
        event_ids.append(response.json()["event_id"])

    history = client.get(
        f"/v1/users/{user_id}/risk-history?limit=1&offset=0",
        headers={"X-API-Key": api_key},
    )
    history_log = json.loads(caplog.records[-1].getMessage())
    second_page = client.get(
        f"/v1/users/{user_id}/risk-history?limit=1&offset=1",
        headers={"X-API-Key": api_key},
    )
    metrics = client.get("/metrics")

    assert history.status_code == 200
    assert history.json()["events"][0]["event_id"] == event_ids[2]
    assert history.json()["events"][0]["timestamp"].startswith("2026-11-25T14:00:00")
    assert history.json()["limit"] == 1
    assert history.json()["offset"] == 0
    assert set(history.json()["events"][0]) == {
        "event_id",
        "timestamp",
        "risk_score",
        "decision",
        "reasons",
    }
    assert second_page.status_code == 200
    assert second_page.json()["events"][0]["event_id"] == event_ids[1]
    assert history_log["path"] == "/v1/users/{user_id}/risk-history"
    assert user_id not in json.dumps(history_log)
    assert metrics.status_code == 200
    assert ('path="/v1/users/{user_id}/risk-history"') in metrics.text
    assert user_id not in metrics.text


def test_risk_history_requires_api_key(client: TestClient) -> None:
    response = client.get("/v1/users/user-1/risk-history")

    assert response.status_code == 401


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
def test_risk_history_rejects_invalid_pagination(
    client: TestClient,
    api_key: str,
    query: str,
) -> None:
    response = client.get(
        f"/v1/users/user-1/risk-history?{query}",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 422


def test_api_rate_limit_applies_to_valid_api_key_across_endpoints(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.main.get_redis_client", lambda: redis_client)
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_key=SecretStr(api_key),
        rate_limit_enabled=True,
        rate_limit_max_requests=1,
        rate_limit_window_seconds=60,
    )

    invalid_key = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": "not-the-configured-key"},
    )
    first = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": api_key},
    )
    limited = client.get(
        "/v1/users/u1/risk-history",
        headers={"X-API-Key": api_key},
    )

    assert invalid_key.status_code == 401
    assert redis_client.dbsize() == 1
    assert first.status_code == 200
    assert limited.status_code == 429
    assert 1 <= int(limited.headers["Retry-After"]) <= 60


def test_api_rate_limiter_fails_closed_when_redis_is_unavailable(
    client: TestClient,
    api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable_client() -> fakeredis.FakeRedis:
        raise RedisConnectionError("test Redis outage")

    monkeypatch.setattr("app.main.get_redis_client", unavailable_client)
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_key=SecretStr(api_key),
        rate_limit_enabled=True,
    )

    response = client.get(
        "/v1/users/u1/risk-history",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 503


def test_evaluate_updates_profile_after_trusted_login(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
) -> None:
    response = client.post(
        "/v1/login-events/evaluate",
        json=login_event,
        headers={"X-API-Key": api_key},
    )

    profile = UserProfileRepository(db_session).get_by_user_id("u1")

    assert response.status_code == 200
    assert profile is not None
    assert profile.usual_devices == ["d1"]
    assert profile.usual_countries == []
    assert profile.usual_hours == [12]


def test_evaluate_updates_profile_country_for_allowed_new_device_and_country(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_lookup_ip(ip: object, *, db_path: Path | None = None) -> GeoIPResult:
        assert str(ip) == "203.0.113.5"
        return GeoIPResult("us", "Example", 0.0, 0.0)

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

    profile = UserProfileRepository(db_session).get_by_user_id("u1")

    assert response.status_code == 200
    assert response.json()["decision"] == "allow"
    assert response.json()["reasons"] == ["new_device_and_country"]
    assert profile is not None
    assert profile.usual_devices == ["d1"]
    assert profile.usual_countries == ["US"]
    assert profile.usual_hours == [12]


def test_evaluate_does_not_update_profile_for_failed_or_high_risk_login(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
) -> None:
    failed_event = {**login_event, "user_id": "failed-user", "success": False}
    failed_response = client.post(
        "/v1/login-events/evaluate",
        json=failed_event,
        headers={"X-API-Key": api_key},
    )

    app.dependency_overrides[get_settings] = lambda: Settings(
        api_key=SecretStr(api_key),
        high_risk_ip_networks=["203.0.113.0/24"],
    )
    risky_event = {**login_event, "user_id": "risky-user"}
    risky_response = client.post(
        "/v1/login-events/evaluate",
        json=risky_event,
        headers={"X-API-Key": api_key},
    )

    assert failed_response.status_code == 200
    assert risky_response.status_code == 200
    assert risky_response.json()["decision"] == "challenge"
    assert UserProfileRepository(db_session).get_by_user_id("failed-user") is None
    assert UserProfileRepository(db_session).get_by_user_id("risky-user") is None


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


def test_evaluate_does_not_flag_successful_distinct_users_on_shared_ip(
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
    assert response.json()["risk_score"] == 0
    assert response.json()["reasons"] == []


@pytest.mark.parametrize(
    (
        "scenario",
        "history",
        "current_success",
        "window_seconds",
        "expected_score",
        "expected_reasons",
    ),
    [
        (
            "different failed users and devices",
            (
                (4, "user-2", "device-2", False, "203.0.113.5"),
                (3, "user-3", "device-3", False, "203.0.113.5"),
                (2, "user-4", "device-4", False, "203.0.113.5"),
                (1, "user-5", "device-5", False, "203.0.113.5"),
            ),
            False,
            300,
            60,
            ["credential_stuffing_multiple_users_and_devices"],
        ),
        (
            "different users sharing one device",
            tuple(
                (minute, f"user-{minute + 1}", "shared-device", False, "203.0.113.5")
                for minute in range(1, 5)
            ),
            False,
            300,
            0,
            [],
        ),
        (
            "one user using different devices",
            tuple(
                (minute, "user-1", f"device-{minute + 1}", False, "203.0.113.5")
                for minute in range(1, 4)
            ),
            False,
            300,
            0,
            [],
        ),
        (
            "different IP addresses",
            tuple(
                (
                    minute,
                    f"user-{minute + 1}",
                    f"device-{minute + 1}",
                    False,
                    f"198.51.100.{minute}",
                )
                for minute in range(1, 5)
            ),
            False,
            300,
            0,
            [],
        ),
        (
            "legitimate successful logins sharing one IP",
            tuple(
                (
                    minute,
                    f"user-{minute + 1}",
                    f"device-{minute + 1}",
                    True,
                    "203.0.113.5",
                )
                for minute in range(1, 6)
            ),
            True,
            300,
            0,
            [],
        ),
        (
            "successful attempts do not satisfy failed identity threshold",
            (
                (4, "user-2", "device-2", False, "203.0.113.5"),
                (3, "user-3", "device-3", False, "203.0.113.5"),
                (2, "user-4", "device-4", False, "203.0.113.5"),
                (1, "user-5", "device-5", True, "203.0.113.5"),
            ),
            False,
            300,
            0,
            [],
        ),
        (
            "failed attempts outside configured window",
            tuple(
                (
                    minute,
                    f"user-{minute + 1}",
                    f"device-{minute + 1}",
                    False,
                    "203.0.113.5",
                )
                for minute in range(1, 5)
            ),
            False,
            120,
            0,
            [],
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_evaluate_scores_shared_ip_failed_user_and_device_patterns(
    client: TestClient,
    api_key: str,
    login_event: dict[str, object],
    db_session: Session,
    scenario: str,
    history: tuple[tuple[int, str, str, bool, str], ...],
    current_success: bool,
    window_seconds: int,
    expected_score: int,
    expected_reasons: list[str],
) -> None:
    del scenario
    timestamp = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    repository = LoginEventRepository(db_session)
    for minutes_ago, user_id, device_id, success, ip in history:
        repository.add(
            LoginEvent(
                user_id=user_id,
                ip=ip,
                device_id=device_id,
                user_agent="browser",
                timestamp=timestamp - timedelta(minutes=minutes_ago),
                success=success,
                reasons=[],
            )
        )
    db_session.commit()
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_key=SecretStr(api_key),
        credential_stuffing_window_seconds=window_seconds,
    )
    current_event = {
        **login_event,
        "user_id": "user-1",
        "device_id": "device-1",
        "success": current_success,
    }

    response = client.post(
        "/v1/login-events/evaluate",
        json=current_event,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json()["risk_score"] == expected_score
    assert response.json()["reasons"] == expected_reasons


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
