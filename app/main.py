import json
import logging
from pathlib import Path
from secrets import compare_digest
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.db.session import get_session
from app.evaluation import evaluate_and_store
from app.schemas import LoginEventRequest, LoginEventResponse
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
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    request_logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((perf_counter() - started_at) * 1000, 3),
            },
            separators=(",", ":"),
        )
    )
    return response


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demo", include_in_schema=False)
def demo_page() -> FileResponse:
    return FileResponse(Path(__file__).with_name("demo.html"))


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
    return evaluate_and_store(event, session, settings)
