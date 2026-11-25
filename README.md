# Suspicious Login Detection API

> **Project status:** Phase 4 rule-engine work is underway. The rule base and registry are implemented; concrete rules and the login-evaluation pipeline are still being added. See [PLAN.md](./PLAN.md) for the implementation sequence.

## Overview

The planned service evaluates login attempts and returns a risk score from 0 to 100, a decision (`allow`, `challenge`, or `deny`), and explanatory reasons. The design combines deterministic rules with an Isolation Forest anomaly-detection model.

Planned capabilities include:

- FastAPI login-event evaluation API
- API-key authentication for login evaluation
- JSON request logging with generated request IDs
- SQLAlchemy event/profile tables and repositories (implemented)
- Redis failed-attempt counters with TTL (implemented)
- MaxMind GeoLite2 IP lookup for country, city, and coordinates (implemented)
- User-agent parsing for browser, OS, and device type (implemented)
- Required travel-speed calculation between two located logins (implemented)
- New-device and new-country profile comparisons (implemented)
- Time-of-day deviation from usual UTC login hours (implemented)
- Rolling failed-attempt counts for 1, 5, and 60 minutes (implemented)
- Membership checks against supplied high-risk IP/CIDR lists (implemented)
- Typed rule base and deterministic registry (implemented)
- Additional login behavior features
- Concrete scoring rules, API integration, and machine-learning anomaly scoring
- Feedback and monitoring endpoints

The health endpoint, stub evaluation endpoint, settings, API-key authentication, JSON request logging, event/profile data layer, repositories, Redis counters, standalone GeoLite2 lookup, user-agent parsing, feature calculations, IP reputation list matching, and typed rule base/registry are implemented. Concrete rules and login-evaluation integration are still in progress. Machine learning and other planned capabilities are not yet available.

## Prerequisites

For the planned application:

- Python 3.12
- Docker and Docker Compose for the planned containerized deployment
- PostgreSQL and Redis for the planned production-style local stack; SQLite is planned for development

Only Python is needed to run the API locally. Configure a non-empty `API_KEY` to use the login-evaluation endpoint. A local GeoLite2 City database is additionally required only when calling the standalone GeoIP helper.

## Installation

### Manual installation

The project targets Python 3.12 or newer. From the repository root, create and activate a virtual environment, then install the application and development dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Start the API locally with:

```powershell
uvicorn app.main:app --reload
```

Configuration names and safe local defaults are listed in [.env.example](./.env.example). Copy that file to `.env` and set a private `API_KEY` only when configuring a local environment. Never commit `.env` or real credentials.

### Docker installation

Docker support is planned for Phase 7. The `Dockerfile` and Compose configuration do not exist yet, so there is no working Docker install command.

## Configuration

Settings are loaded from environment variables or a `.env` file using `pydantic-settings`. The template is [.env.example](./.env.example); copy it to `.env` for local configuration. The variables below are now recognized by the application:

| Variable | Purpose | Status |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy database connection string | Default: local SQLite URL; PostgreSQL is supported with psycopg |
| `REDIS_URL` | Redis connection string for failed-attempt counters | Default: local Redis URL; Redis must be running to use the counters |
| `GEOIP_DB_PATH` | Path to the GeoLite2 City database used by the IP lookup | Default: `data/GeoLite2-City.mmdb`; the database file must be obtained separately |
| `SHADOW_MODE` | Evaluate decisions without enforcing them | Default: `true`; enforcement behavior planned in Phase 4 |
| `MODEL_PATH` | Location of the trained model artifact | Default: `artifacts/model.joblib`; model support planned in Phase 5 |
| `API_KEY` | API-key authentication secret for login evaluation | Required; when empty, evaluation requests return `503 Service Unavailable` |

`API_KEY` is stored as a secret value and is not included in its normal string representation. Do not put a real key in source control.

## GeoIP lookup

`lookup_ip` reads a MaxMind GeoLite2 City database at `GEOIP_DB_PATH` and returns the country ISO code, city name, latitude, and longitude. It returns `None` when the database has no record for the address. Invalid IP strings and missing or unreadable database files raise errors rather than silently producing a location. The `.mmdb` file is not included in the repository. The login-evaluation endpoint does not yet call this helper.

### Downloading and configuring the database

1. [Create a MaxMind account](https://www.maxmind.com/en/geolite-free-ip-geolocation-data), review and accept the [GeoLite End User License Agreement](https://www.maxmind.com/en/geolite2/eula), then [generate a license key](https://support.maxmind.com/knowledge-base/articles/generate-a-maxmind-license-key).
2. Install the official [GeoIP Update utility](https://github.com/maxmind/geoipupdate/releases). MaxMind recommends it for binary `.mmdb` databases; see the [GeoLite guide](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data/) and [update instructions](https://dev.maxmind.com/geoip/updating-databases/).
3. Use the pre-filled `GeoIP.conf` available from your MaxMind account, keeping the file outside the repository. Set its edition to `EditionIDs GeoLite2-City`. It contains account credentials; never commit it or put its credentials in source code or logs.
4. From the repository root in PowerShell, download the database into the git-ignored `data/` directory:

   ```powershell
   New-Item -ItemType Directory -Force .\data | Out-Null
   geoipupdate -f "C:\path\outside\repository\GeoIP.conf" -d ".\data"
   Test-Path .\data\GeoLite2-City.mmdb
   ```

   The final command should return `True`.
5. The default `GEOIP_DB_PATH` in [.env.example](./.env.example) already points to `data/GeoLite2-City.mmdb`. Set it in your ignored `.env` only if you store the database elsewhere.

GeoLite locations are approximate areas, not precise addresses or households; treat coordinates and travel-speed features as risk signals rather than proof of a user's physical location. MaxMind requires GeoLite databases to be kept current and outdated copies deleted within 30 days of a new release. See the [official update guidance](https://dev.maxmind.com/geoip/updating-databases/). GeoIP unit tests stub the database reader and do not require a downloaded database.

## User-agent parsing

`parse_user_agent` returns the parsed browser family, operating-system family, and a device class (`bot`, `tablet`, `mobile`, `desktop`, or `other`). Unknown non-empty strings produce `Other` browser/OS families and the `other` class; empty or whitespace-only input raises `ValueError`. This helper is not yet wired into the login-evaluation endpoint.

`required_travel_speed_kmh` computes the Haversine distance between two GeoIP results and divides by the elapsed time. It returns `None` when either location or its coordinates are missing, requires timezone-aware timestamps in increasing order, and reports speed in km/h. It is a standalone feature helper, not yet connected to the API.

`detect_new_login_signals` compares a device ID and country code with a user's `UserProfile`. Device IDs are matched exactly; country codes are matched case-insensitively. A missing profile is treated as empty history, while a missing country does not set the new-country flag.

`time_of_day_deviation_hours` compares the login's UTC hour with the nearest `usual_hours` entry using circular 24-hour distance, returning 0–12 hours. It returns `None` when no profile hours are available and rejects naive timestamps or profile hours outside 0–23. Profile hours must therefore use UTC.

## Database

The synchronous SQLAlchemy engine reads `DATABASE_URL` from the environment or `.env`. SQLite is the local default, and PostgreSQL is supported through psycopg. Alembic reads the same setting. Apply the migrations from the repository root to create the `login_events` and `user_profiles` tables:

```powershell
alembic upgrade head
```

The migration command and schema checks were verified with SQLite. The PostgreSQL driver is configured, but a live PostgreSQL connection has not been exercised. The `login_events` table stores event details, optional JSON geographic data, and validated risk output. Each `user_profiles` row stores a user's usual countries, devices, and login hours as JSON arrays.

`LoginEventRepository` provides event insertion, lookup, and paginated per-user history; `UserProfileRepository` loads and saves profiles. Repository methods flush changes, while the caller owns the session transaction and commit.

`FailedAttemptCounter` stores per-user counters in Redis with a configurable fixed-window TTL. User identifiers are hashed in Redis keys; the counter sets the expiry atomically on the first failure in each window. Separate window lengths use separate counters. A Redis server must be available when these counters are used. The current login-evaluation endpoint does not yet call the repositories or counters.

`FailedAttemptVelocity` separately records individual failures in per-user Redis sorted sets and atomically returns rolling counts for the inclusive last 1, 5, and 60 minutes. User IDs are hashed; each write prunes entries older than one hour and refreshes the set's one-hour TTL. The failure-recording method must be called by its consumer; the evaluation endpoint does not yet record attempts.

`HighRiskIPList` matches IPv4/IPv6 addresses against supplied individual IPs and CIDR networks. It ships no VPN, Tor, proxy, or other reputation feed; callers must provide and maintain a trusted list. Invalid addresses or list entries raise `ValueError`. This helper is not yet wired into the evaluation endpoint.

## Rule engine

Rules receive an immutable `RuleContext` containing precomputed login signals. Each rule has a unique name, an integer weight from 0 to 100, and a condition; `RuleRegistry` evaluates rules in registration order and returns the matches. `ImpossibleTravelRule` triggers strictly above 900 km/h and has a default weight of 40, enough to reach the `challenge` range on its own. Additional concrete rules and API integration are being added in Phase 4.

## API

Implemented and planned core endpoints:

| Method | Path | Purpose | Planned step |
|---|---|---|---|
| `GET` | `/health` | Health check (`{"status":"ok"}`) | 1.1 — implemented |
| `POST` | `/v1/login-events/evaluate` | Evaluate a login event (stub: always returns `allow`); requires `X-API-Key` | 1.4–1.5 — implemented |
| `POST` | `/v1/feedback` | Submit a feedback label | 6.1 |
| `GET` | `/v1/users/{id}/risk-history` | Retrieve a user's risk history | 6.4 |

The login-event request and response schemas are defined, and the evaluation endpoint currently returns a stub response.
Set `API_KEY` in the environment or `.env`, then include it in the `X-API-Key` request header. The health endpoint remains public. Requests to the evaluation endpoint receive `401 Unauthorized` for a missing or incorrect key.
Each response includes a generated `X-Request-ID`; the server logs the method, path, status, duration, and request ID as a JSON object without logging request bodies or authentication headers.

Request:

```json
{
  "user_id": "u_123",
  "ip": "203.0.113.5",
  "user_agent": "Mozilla/5.0 ...",
  "device_id": "d_abc",
  "timestamp": "2026-11-25T12:00:00Z",
  "success": true
}
```

The stub response always allows the event; risk evaluation and reasons are not implemented yet.

Planned response example (the current stub instead always returns `allow`):

```json
{
  "event_id": "evt_001",
  "risk_score": 78,
  "decision": "challenge",
  "reasons": ["impossible_travel", "new_device"]
}
```

The clarified planned thresholds are `0–39 → allow`, `40–78 → challenge`, and `79–100 → deny`. Scoring is not implemented yet.

## Model training

Model training and evaluation are planned for Phase 5. The training script is planned at `scripts/train.py`; neither it nor the model artifacts exist yet. Training, inference, and evaluation commands will be added once implemented and tested.

## Tests and quality checks

Run the API test suite and configured quality checks from the repository root:

```powershell
pytest -q
ruff check .
mypy app
pre-commit run --all-files
```

The development extra installs pytest, `httpx2` for Starlette's TestClient, and Lua-enabled `fakeredis` for counter tests without a Redis server. GeoIP unit tests stub the database reader and do not require a GeoLite2 file; user-agent parsing tests use local parser data and make no network requests. Repository tests apply Alembic migrations to isolated temporary SQLite databases. The pre-commit hooks run TOML/YAML and whitespace checks, Ruff lint/format, and mypy.

The editable installation, API tests, and listed quality checks were verified with Python 3.14. The project requires Python 3.12 or newer.

## Project structure

Current files:

```text
.
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── alembic.ini
├── alembic/
│   ├── README
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── AGENTS.md
├── app/
│   ├── __init__.py
│   ├── db/
│   │   ├── base.py
│   │   ├── models.py
│   │   ├── repositories.py
│   │   └── session.py
│   ├── features.py
│   ├── geoip.py
│   ├── ip_reputation.py
│   ├── main.py
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── registry.py
│   ├── redis_counters.py
│   ├── schemas.py
│   ├── settings.py
│   └── user_agent.py
├── docs/
├── LICENSE
├── PLAN.md
├── README.md
├── pyproject.toml
├── scripts/
└── tests/
    ├── conftest.py
    ├── test_api.py
    ├── test_features.py
    ├── test_geoip.py
    ├── test_ip_reputation.py
    ├── test_redis_counters.py
    ├── test_repositories.py
    ├── test_rules.py
    └── test_user_agent.py
```

`app/` contains the service and data layer, `alembic/` database migrations, `tests/` API and data-layer tests, `scripts/` model and maintenance scripts, and `docs/` supplementary documentation.

## Troubleshooting

- **Cannot start the API:** install the project with `python -m pip install -e ".[dev]"` and run `uvicorn app.main:app --reload` from the repository root.
- **Docker Compose files not found:** Docker support is planned for Phase 7 and has not been added.
- **Evaluation requests return 503:** set a non-empty `API_KEY` in the environment or `.env`; the service fails closed when authentication is not configured.
- **Redis connection errors:** start Redis at the configured `REDIS_URL` before using failed-attempt counters.
- **Model commands are unavailable:** training and evaluation scripts are planned for Phase 5 and have not been added.

## Privacy and security

The plan calls for API keys to come from environment configuration and never be logged. IP addresses and device IDs should be hashed or masked where possible, and retention and user-data deletion requirements should be addressed before production use. Deny decisions should initially run in shadow mode to measure false positives.
