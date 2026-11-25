from prometheus_client import CollectorRegistry, Counter, Histogram
from starlette.requests import Request
from starlette.routing import Match

registry = CollectorRegistry()

http_requests = Counter(
    "sus_http_requests",
    "HTTP requests completed by the API.",
    ("method", "path", "status_code"),
    registry=registry,
)
http_request_duration = Histogram(
    "sus_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "path"),
    registry=registry,
)
login_decisions = Counter(
    "sus_login_decisions",
    "Login evaluation decisions returned by the API.",
    ("decision",),
    registry=registry,
)


def route_template(request: Request) -> str:
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match is Match.FULL:
            path = getattr(route, "path", None)
            if isinstance(path, str):
                return path
    return "unmatched"
