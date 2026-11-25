# Suspicious Login Detection API

> **Project status:** Phase 4 rule-engine MVP is complete. Phase 5 is underway: synthetic data generation, Isolation Forest training, a versioned registry, and standalone inference are implemented. API score blending and model evaluation are next. See [PLAN.md](./PLAN.md) for the implementation sequence.

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
- Explainable rule conditions and weighted scoring (implemented)
- Reproducible generator for labeled synthetic login-feature data (implemented)
- Isolation Forest training from generated normal events (implemented)
- Standalone model inference with a bounded anomaly risk score (implemented)
- Additional login behavior features
- Machine-learning anomaly scoring (in progress)
- Feedback and monitoring endpoints

The health endpoint, login-event evaluation, settings, API-key authentication, JSON request logging, event/profile data layer, repositories, Redis counters, standalone GeoLite2 lookup, user-agent parsing, feature calculations, IP reputation list matching, rule conditions, weighted scoring, local test page, synthetic training-data generator, Isolation Forest training script, versioned model registry, and standalone inference service are implemented. The HTTP endpoint still uses rule-only scoring until Phase 5.5; evaluation and other planned capabilities are not yet available.

## Prerequisites

For the planned application:

- Python 3.12
- Docker and Docker Compose for the planned containerized deployment
- PostgreSQL and Redis for the planned production-style local stack; SQLite is planned for development

Only Python is needed to run the API locally. Configure a non-empty `API_KEY` to use the login-evaluation endpoint. A local GeoLite2 City database is required for the standalone GeoIP helper and only when enabling GeoIP in login evaluation.

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
alembic upgrade head
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
| `GEOIP_ENABLED` | Use GeoLite2 lookup during login evaluation | Default: `false`; set to `true` only after obtaining the database |
| `HIGH_RISK_IP_NETWORKS` | JSON list of IPv4/IPv6 addresses and CIDRs for the high-risk rule | Default: `[]` |
| `ALLOW_MAX_SCORE` | Highest score classified as `allow` | Default: `39`; must be lower than `CHALLENGE_MAX_SCORE` |
| `CHALLENGE_MAX_SCORE` | Highest score classified as `challenge` | Default: `78`; scores above this are `deny` |
| `SHADOW_MODE` | Advisory marker for downstream enforcement | Default: `true`; the API returns the same score/decision in either mode and never blocks logins |
| `MODEL_PATH` | Base path for the versioned model registry | Default: `artifacts/model.joblib`; writes numbered artifacts and a `model.json` latest-version manifest |
| `API_KEY` | API-key authentication secret for login evaluation | Required; when empty, evaluation requests return `503 Service Unavailable` |

`API_KEY` is stored as a secret value and is not included in its normal string representation. Do not put a real key in source control.

## GeoIP lookup

`lookup_ip` reads a MaxMind GeoLite2 City database at `GEOIP_DB_PATH` and returns the country ISO code, city name, latitude, and longitude. It returns `None` when the database has no record for the address. Invalid IP strings and missing or unreadable database files raise errors rather than silently producing a location. The `.mmdb` file is not included in the repository. Login evaluation uses this helper only when `GEOIP_ENABLED=true`; the default `false` keeps local evaluation usable without downloading a database.

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

`required_travel_speed_kmh` computes the Haversine distance between two GeoIP results and divides by the elapsed time. It returns `None` when either location or its coordinates are missing, requires timezone-aware timestamps in increasing order, and reports speed in km/h. Login evaluation uses this helper when GeoIP is enabled and a previous located event exists.

`detect_new_login_signals` compares a device ID and country code with a user's `UserProfile`. Device IDs are matched exactly; country codes are matched case-insensitively. A missing profile is treated as empty history, while a missing country does not set the new-country flag.

`time_of_day_deviation_hours` compares the login's UTC hour with the nearest `usual_hours` entry using circular 24-hour distance, returning 0–12 hours. It returns `None` when no profile hours are available and rejects naive timestamps or profile hours outside 0–23. Profile hours must therefore use UTC.

## Database

The synchronous SQLAlchemy engine reads `DATABASE_URL` from the environment or `.env`. SQLite is the local default, and PostgreSQL is supported through psycopg. Alembic reads the same setting. Apply the migrations from the repository root to create the `login_events` and `user_profiles` tables:

```powershell
alembic upgrade head
```

The migration command and schema checks were verified with SQLite. The PostgreSQL driver is configured, but a live PostgreSQL connection has not been exercised. The `login_events` table stores event details, optional JSON geographic data, and validated risk output. Each `user_profiles` row stores a user's usual countries, devices, and login hours as JSON arrays.

`LoginEventRepository` provides event insertion, lookup, paginated per-user history, prior-event lookup, and distinct-user queries by IP/time window; `UserProfileRepository` loads and saves profiles. Repository methods flush changes, while the caller owns the session transaction and commit. Login evaluation commits its stored result after computing the score.

`FailedAttemptCounter` stores per-user counters in Redis with a configurable fixed-window TTL. User identifiers are hashed in Redis keys; the counter sets the expiry atomically on the first failure in each window. Separate window lengths use separate counters. A Redis server must be available when these counters are used. Login evaluation currently uses stored events for brute-force and credential-stuffing signals and does not depend on Redis.

`FailedAttemptVelocity` separately records individual failures in per-user Redis sorted sets and atomically returns rolling counts for the inclusive last 1, 5, and 60 minutes. User IDs are hashed; each write prunes entries older than one hour and refreshes the set's one-hour TTL. It remains a standalone helper; login evaluation uses persisted event history for the current rules.

`HighRiskIPList` matches IPv4/IPv6 addresses against the configured `HIGH_RISK_IP_NETWORKS` list. No VPN, Tor, proxy, or other reputation feed is bundled; operators must supply and maintain a trusted list.

## Rule engine

Rules receive an immutable `RuleContext` containing precomputed login signals. Each rule has a unique name, an integer weight from 0 to 100, and a condition; `RuleRegistry` evaluates rules in registration order and returns the matches. `ImpossibleTravelRule` triggers strictly above 900 km/h with weight 40. `BruteForceRule` triggers at five consecutive failures or five distinct users from one IP within five minutes, with weight 60. `NewDeviceAndCountryRule` triggers only when both signals are true, with weight 30. `HighRiskIPRule` triggers on a supplied high-risk IP match, with weight 40. `UnusualHourRule` triggers at a six-hour or greater deviation from a user's usual UTC login hours, with weight 15.

`aggregate_score` sums the weights of triggered rules and caps the score at 100. `score_to_decision` uses `ALLOW_MAX_SCORE` and `CHALLENGE_MAX_SCORE`, defaulting to `0–39 → allow`, `40–78 → challenge`, and `79–100 → deny`. Both threshold values are validated at startup and can be overridden with environment variables. Login evaluation builds rule context from saved event history, user profiles, and configured GeoIP/reputation sources, then stores the evaluation result.

`SHADOW_MODE=true` is the safe default for an authentication service integrating this API. This service always returns its calculated score, decision, and reasons; it does not itself block or authenticate logins. The setting does not change the response, and setting it to `false` alone does not add enforcement. A downstream authentication service must decide whether to act on the returned recommendation.

## API

Implemented and planned core endpoints:

| Method | Path | Purpose | Planned step |
|---|---|---|---|
| `GET` | `/health` | Health check (`{"status":"ok"}`) | 1.1 — implemented |
| `GET` | `/demo` | Local browser page for submitting test login events | 4.8 — implemented |
| `POST` | `/v1/login-events/evaluate` | Evaluate and store a login event with risk score, decision, and reasons; requires `X-API-Key` | 1.4–1.5, 4.8 — implemented |
| `POST` | `/v1/feedback` | Submit a feedback label | 6.1 |
| `GET` | `/v1/users/{id}/risk-history` | Retrieve a user's risk history | 6.4 |

Set `API_KEY` in the environment or `.env`, then include it in the `X-API-Key` request header. The health and demo pages are public; evaluation requests receive `401 Unauthorized` for a missing or incorrect key. Request timestamps must include a timezone. Apply the SQLite migration with `alembic upgrade head` before evaluating events. GeoIP lookup is disabled by default; enable it only after configuring a valid database path. Each evaluation is saved to `login_events`; user profiles are read but not automatically updated.
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

```json
{
  "event_id": "evt_001",
  "risk_score": 78,
  "decision": "challenge",
  "reasons": ["impossible_travel", "new_device"]
}
```

The response contains the weighted rule result. Default thresholds are `0–39 → allow`, `40–78 → challenge`, and `79–100 → deny`. These decisions are recommendations only; the API does not enforce them.

### Local test page

After applying migrations and starting the API, open `http://127.0.0.1:8000/demo`, enter the configured API key, and submit an event. Uncheck **Login succeeded** and submit five attempts for the same user to exercise the brute-force rule. The page refreshes its UTC timestamp on each submission and displays the actual API response. It keeps the key in page memory only and sends it to the same origin; use it for local development, not shared or production browsers.

## Model training

Generate a deterministic CSV of numeric login features and normal/suspicious labels, then train an Isolation Forest using only the normal rows:

```powershell
python scripts/generate_synthetic_data.py --output .\data\synthetic-login-events.csv --normal-count 1000 --suspicious-count 100 --seed 42
python scripts/train.py --input .\data\synthetic-login-events.csv --output .\artifacts\model.joblib --seed 42
```

The generated dataset contains no real users, IP addresses, or credentials and is written under the git-ignored `data/` directory by default. Training requires `scikit-learn` and uses `MODEL_PATH` as the base path for versioned artifacts, metadata, and the latest-version manifest. `InferenceService` loads the registered Isolation Forest and returns a bounded anomaly risk score from its decision function; this score is not a probability. The API does not blend model and rule scores until Phase 5.5. Evaluation is being implemented in the remaining Phase 5 steps.

## Tests and quality checks

Run the API test suite and configured quality checks from the repository root:

```powershell
pytest -q
ruff check .
mypy app
pre-commit run --all-files
```

The development extra installs pytest, `httpx2` for Starlette's TestClient, and Lua-enabled `fakeredis` for counter tests without a Redis server. GeoIP unit tests stub the database reader and do not require a GeoLite2 file; user-agent parsing tests use local parser data and make no network requests. Repository and API tests apply Alembic migrations to isolated temporary SQLite databases. Rule tests cover each condition's boundaries, score aggregation, decision thresholds, history windows, authentication, and API responses. The pre-commit hooks run TOML/YAML and whitespace checks, Ruff lint/format, and mypy.

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
│   ├── ml_data.py
│   ├── ml_features.py
│   ├── ml_inference.py
│   ├── ml_training.py
│   ├── model_registry.py
│   ├── db/
│   │   ├── base.py
│   │   ├── models.py
│   │   ├── repositories.py
│   │   └── session.py
│   ├── features.py
│   ├── evaluation.py
│   ├── demo.html
│   ├── geoip.py
│   ├── ip_reputation.py
│   ├── main.py
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── registry.py
│   ├── redis_counters.py
│   ├── scoring.py
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
    ├── test_scoring.py
    └── test_user_agent.py
```

`app/` contains the service and data layer, `alembic/` database migrations, `tests/` API and data-layer tests, `scripts/` model and maintenance scripts, and `docs/` supplementary documentation.

## Troubleshooting

- **Cannot start the API:** install the project with `python -m pip install -e ".[dev]"` and run `uvicorn app.main:app --reload` from the repository root.
- **Docker Compose files not found:** Docker support is planned for Phase 7 and has not been added.
- **Evaluation requests return 503:** set a non-empty `API_KEY` in the environment or `.env`; the service fails closed when authentication is not configured.
- **Evaluation requests fail with a database error:** run `alembic upgrade head` before starting the API.
- **Redis connection errors:** start Redis at the configured `REDIS_URL` before using failed-attempt counters.
- **The API does not use model scores yet:** the standalone inference service is implemented, but blending into login evaluation is Phase 5.5. Model evaluation is planned for Phase 5.6.

## Privacy and security

The plan calls for API keys to come from environment configuration and never be logged. IP addresses and device IDs should be hashed or masked where possible, and retention and user-data deletion requirements should be addressed before production use. Deny decisions should initially run in shadow mode to measure false positives.
