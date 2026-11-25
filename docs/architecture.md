# Architecture

The diagram shows the request path and optional integrations. The API can run with
SQLite and no model or GeoIP database; PostgreSQL and Redis are available in the
local Compose stack.

```mermaid
flowchart LR
    client[API client]

    subgraph service[FastAPI service]
        middleware[Request logging and metrics middleware] --> routes[FastAPI routes]
        routes --> auth[API-key authentication]
        auth -->|rate limit enabled| limiter[Redis rate limiter]
        auth -->|login evaluation| evaluate[Evaluation service]
        evaluate --> features[Feature and profile signals]
        features --> rules[Deterministic rule engine]
        rules --> score[Risk score and decision]
        score -. optional .-> model[Isolation Forest model registry]
        evaluate -. optional .-> geoip[GeoLite2 database]
        routes --> repositories[SQLAlchemy repositories]
        evaluate --> repositories
        repositories --> db[(SQLite or PostgreSQL)]
        middleware --> metrics[Prometheus registry]
        routes --> metrics_endpoint["/metrics"]
        metrics_endpoint --> metrics
    end

    client --> middleware
    limiter --> redis[(Redis)]
```

Protected endpoints require `X-API-Key`. Login evaluation reads recent events
and user profiles, applies rule-based scoring, optionally blends a trained
model score, then persists the event and any eligible trusted-login profile
update. Feedback and risk-history requests use the same relational database.
Redis is contacted for API-key rate limiting only when that feature is enabled.

See the interactive [OpenAPI documentation](http://127.0.0.1:8000/docs) for
request and response examples. The API uses reserved documentation IP ranges
and synthetic identifiers in its examples; replace them with suitable test data.
