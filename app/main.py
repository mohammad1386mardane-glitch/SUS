import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from secrets import compare_digest
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Security, status
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.db.models import LoginFeedback
from app.db.repositories import LoginEventRepository, LoginFeedbackRepository
from app.db.session import get_session
from app.evaluation import evaluate_and_store
from app.metrics import (
    http_request_duration,
    http_requests,
    login_decisions,
    registry,
    route_template,
)
from app.rate_limit import ApiKeyRateLimiter
from app.redis_counters import get_redis_client
from app.schemas import (
    Decision,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    LoginEventRequest,
    LoginEventResponse,
    RiskHistoryEntry,
    RiskHistoryResponse,
)
from app.settings import Settings, get_settings

app = FastAPI(title="Suspicious Login Detection API")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
request_logger = logging.getLogger("app.request")


@app.middleware("http")
async def log_request(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    request_id = uuid4().hex
    request.state.request_id = request_id
    started_at = perf_counter()
    path = route_template(request)
    response = await call_next(request)
    duration = perf_counter() - started_at
    response.headers["X-Request-ID"] = request_id
    http_requests.labels(request.method, path, str(response.status_code)).inc()
    http_request_duration.labels(request.method, path).observe(duration)
    request_logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 3),
            },
            separators=(",", ":"),
        )
    )
    return response


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/demo", include_in_schema=False)
def demo_page() -> FileResponse:
    return FileResponse(Path(__file__).with_name("demo.html"))


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics() -> Response:
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )


def require_api_key(
    api_key: Annotated[str | None, Security(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    configured_api_key = settings.api_key.get_secret_value()
    if not configured_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key authentication is not configured",
        )
    if api_key is None or not compare_digest(
        api_key.encode("utf-8"), configured_api_key.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    if settings.rate_limit_enabled:
        try:
            rate_limit_window = ApiKeyRateLimiter(get_redis_client()).consume(
                api_key,
                window_seconds=settings.rate_limit_window_seconds,
            )
        except RedisError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API rate limiter is unavailable",
            ) from error
        if rate_limit_window.request_count > settings.rate_limit_max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API rate limit exceeded",
                headers={"Retry-After": str(rate_limit_window.retry_after_seconds)},
            )


@app.post(
    "/v1/login-events/evaluate",
    response_model=LoginEventResponse,
    dependencies=[Depends(require_api_key)],
)
def evaluate_login_event(
    event: LoginEventRequest,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginEventResponse:
    response = evaluate_and_store(event, session, settings)
    login_decisions.labels(response.decision).inc()
    return response


@app.post(
    "/v1/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def submit_feedback(
    feedback: FeedbackRequest,
    session: Annotated[Session, Depends(get_session)],
) -> FeedbackResponse:
    event_repository = LoginEventRepository(session)
    login_event = event_repository.get_by_event_id(feedback.event_id)
    if login_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Login event not found",
        )

    feedback_repository = LoginFeedbackRepository(session)
    if feedback_repository.get_for_login_event(login_event.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback has already been submitted for this event",
        )

    try:
        feedback_repository.add(
            LoginFeedback(login_event_id=login_event.id, label=feedback.label)
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if feedback_repository.get_for_login_event(login_event.id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Feedback has already been submitted for this event",
            ) from error
        raise

    return FeedbackResponse(event_id=feedback.event_id, label=feedback.label)


@app.get(
    "/v1/users/{user_id}/risk-history",
    response_model=RiskHistoryResponse,
    dependencies=[Depends(require_api_key)],
)
def get_user_risk_history(
    user_id: str,
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RiskHistoryResponse:
    events = LoginEventRepository(session).list_for_user(
        user_id,
        limit=limit,
        offset=offset,
    )
    entries: list[RiskHistoryEntry] = []
    for event in events:
        entries.append(
            RiskHistoryEntry(
                event_id=event.event_id,
                timestamp=_as_utc(event.timestamp),
                risk_score=event.risk_score,
                decision=_stored_decision(event.decision),
                reasons=event.reasons,
            )
        )
    return RiskHistoryResponse(events=entries, limit=limit, offset=offset)


def _as_utc(value: datetime) -> datetime:
    if value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _stored_decision(value: str | None) -> Decision | None:
    if value is None:
        return None
    if value == "allow":
        return "allow"
    if value == "challenge":
        return "challenge"
    if value == "deny":
        return "deny"
    raise ValueError("stored login event has an invalid decision")
