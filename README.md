# Suspicious Login Detection API

> **Project status:** Phases 0–7 are complete and the `v1.0.0` release tag is prepared locally. CI, security scanning, and gated GHCR publishing workflows are configured. See [PLAN.md](./PLAN.md) for project status and [docs/architecture.md](./docs/architecture.md) for the system design.

## Overview

The service evaluates login attempts and returns a risk score from 0 to 100, a decision (`allow`, `challenge`, or `deny`), and explanatory reasons. It combines deterministic rules with an optional Isolation Forest anomaly-detection model.

Implemented capabilities include:

- FastAPI login-event evaluation API
- API-key authentication for protected API routes
- JSON request logging with generated request IDs
- SQLAlchemy event/profile tables and repositories (implemented)
- Redis failed-attempt counter helpers with TTL and rolling windows
- MaxMind GeoLite2 IP lookup for country, city, and coordinates (implemented)
- User-agent parsing and same-device profile-change scoring (implemented)
- Required travel-speed calculation between two located logins (implemented)
- New-device and new-country profile comparisons (implemented)
- Profile learning from confirmed low-risk logins (implemented)
- Time-of-day deviation from usual UTC login hours (implemented)
- Rolling failed-attempt counts for 1, 5, and 60 minutes (implemented)
- Membership checks against supplied high-risk IP/CIDR lists (implemented)
- Typed rule base and deterministic registry (implemented)
- Explainable rule conditions and weighted scoring (implemented)
- Reproducible generator for labeled synthetic login-feature data (implemented)
- Isolation Forest training from generated normal events (implemented)
- Standalone model inference with a bounded anomaly risk score (implemented)
- Optional weighted rule/ML score blending in login evaluation (implemented)
- Precision, recall, ROC-AUC, and false-positive evaluation (implemented)
- Prometheus request, latency, and decision metrics at `/metrics` (implemented)
- Optional Redis-backed API-key rate limiting (implemented)
- Authenticated feedback and paginated user risk-history endpoints (implemented)
The health and metrics endpoints, authenticated login evaluation and feedback, paginated risk history, trusted-login profile learning, JSON request logging, event/profile/feedback persistence, optional Redis rate limiting, rule and model scoring, and model training/evaluation workflow are implemented. API scoring remains rule-only by default; enable `ML_ENABLED` after training a model. A local Docker Compose stack and tagged GHCR publishing workflow are available. Production deployment, monitoring, retention, and enforcement policies remain the operator's responsibility.

## Prerequisites

For local development:

- Python 3.12 or newer
- Docker Engine with Docker Compose v2 for the optional container stack

Only Python is needed to run the API locally; SQLite is the local default. The Compose stack starts PostgreSQL and Redis. Configure a non-empty `API_KEY` to use protected endpoints. A local GeoLite2 City database is required only when enabling GeoIP in login evaluation.

## Installation

### Manual installation

The project targets Python 3.12 or newer. From the repository root, create and activate a virtual environment, then install the application and development dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env and set a private, non-empty API_KEY.
# Generate a random value if needed, then copy it into .env:
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Start the API locally with:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

The `.env` file is ignored by Git. Never commit it or real credentials.

### Docker installation

Install Docker Desktop with Docker Compose v2, then create the local environment file and set private API/PostgreSQL credentials:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env and set API_KEY and a URL-safe POSTGRES_PASSWORD.
docker compose build
docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
docker compose up -d api
```

The API listens only on `127.0.0.1:8000`; PostgreSQL and Redis are available only on the Compose network. Use a URL-safe PostgreSQL password (letters, digits, hyphens, and underscores) because Compose embeds it in `DATABASE_URL`. Check `http://127.0.0.1:8000/health` and open `http://127.0.0.1:8000/docs` for the interactive OpenAPI UI. The image uses a non-root user and named volumes for the database, application data, and model artifacts. Stop the stack with `docker compose down`; this preserves named volumes. The Compose stack is intended for local use; use managed secrets and hardened network settings for deployment.

OpenAPI includes example request and response payloads. The service and optional integrations are shown in [docs/architecture.md](./docs/architecture.md).

Pushing a semantic-version tag such as `v1.2.3` runs the Python checks first, then builds and publishes `ghcr.io/<owner>/<repository>` for `linux/amd64` and `linux/arm64` only if they pass. The workflow also publishes the `1.2` tag; stable version tags update `latest`. Pull requests that change the container build inputs run the same checks and build the image without publishing it. After configuring a GitHub remote, push the local release tag with `git push origin v1.0.0` to trigger the release workflow.

## Configuration

Settings are loaded from environment variables or a `.env` file using `pydantic-settings`. The template is [.env.example](./.env.example); copy it to `.env` for local configuration. The variables below are now recognized by the application:

| Variable | Purpose | Default or requirement |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy database connection string | Default: local SQLite URL; PostgreSQL is supported with psycopg |
| `REDIS_URL` | Redis connection string for optional counters and API-key rate limiting | Default: local Redis URL; Redis must be running when these features are used |
| `GEOIP_DB_PATH` | Path to the GeoLite2 City database used by the IP lookup | Default: `data/GeoLite2-City.mmdb`; the database file must be obtained separately |
| `GEOIP_ENABLED` | Use GeoLite2 lookup during login evaluation | Default: `false`; set to `true` only after obtaining the database |
| `HIGH_RISK_IP_NETWORKS` | JSON list of IPv4/IPv6 addresses and CIDRs for the high-risk rule | Default: `[]` |
| `ALLOW_MAX_SCORE` | Highest score classified as `allow` | Default: `39`; must be lower than `CHALLENGE_MAX_SCORE` |
| `CHALLENGE_MAX_SCORE` | Highest score classified as `challenge` | Default: `78`; scores above this are `deny` |
| `SHADOW_MODE` | Advisory marker for downstream enforcement | Default: `true`; the API returns the same score/decision in either mode and never blocks logins |
| `MODEL_PATH` | Base path for the versioned model registry | Default: `artifacts/model.joblib`; writes numbered artifacts and a `model.json` latest-version manifest |
| `ML_ENABLED` | Blend the registered model score into API evaluation | Default: `false`; requires a trained model registered at `MODEL_PATH` |
| `RATE_LIMIT_ENABLED` | Enforce a shared Redis fixed-window limit per valid API key | Default: `false`; requires Redis when enabled |
| `RATE_LIMIT_MAX_REQUESTS` | Maximum protected requests allowed per API key in one window | Default: `100`; must be at least `1` |
| `RATE_LIMIT_WINDOW_SECONDS` | Fixed-window duration for API-key rate limits | Default: `60`; must be at least `1` |
| `CREDENTIAL_STUFFING_WINDOW_SECONDS` | Lookback window for failed shared-IP account/device diversity | Default: `300`; must be at least `1` |
| `API_KEY` | API-key authentication secret for protected API routes | Required; when empty, protected requests return `503 Service Unavailable` |

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

`parse_user_agent` returns browser and operating-system families plus a device class (`bot`, `tablet`, `mobile`, `desktop`, or `other`). During evaluation, the service compares those features with the most recent prior event for the same device among the user's four most recent events. It adds 15 points with reason `user_agent_profile_change` only when at least two recognized dimensions change on a device already present in the user's trusted profile. Browser-version updates and single-dimension changes do not score; new devices are handled by the existing device/country rule instead. Unknown non-empty strings produce `Other` families and the `other` class and do not trigger this rule. Missing or whitespace-only User-Agent values are rejected as invalid requests.

`required_travel_speed_kmh` computes the Haversine distance between two GeoIP results and divides by the elapsed time. It returns `None` when either location or its coordinates are missing, requires timezone-aware timestamps in increasing order, and reports speed in km/h. Login evaluation uses this helper when GeoIP is enabled and a previous located event exists.

`detect_new_login_signals` compares a device ID and country code with a user's `UserProfile`. Device IDs are matched exactly; country codes are matched case-insensitively. A missing profile is treated as empty history, while a missing country does not set the new-country flag.

`time_of_day_deviation_hours` compares the login's UTC hour with the nearest `usual_hours` entry using circular 24-hour distance, returning 0–12 hours. It returns `None` when no profile hours are available and rejects naive timestamps or profile hours outside 0–23. Profile hours must therefore use UTC.

## Database

The synchronous SQLAlchemy engine reads `DATABASE_URL` from the environment or `.env`. SQLite is the local default, and PostgreSQL is supported through psycopg. Alembic reads the same setting. Apply the migrations from the repository root to create the `login_events` and `user_profiles` tables:

```powershell
alembic upgrade head
```

The migration command and schema checks were verified with SQLite. The PostgreSQL driver is configured, but a live PostgreSQL connection has not been exercised. The `login_events` table stores event details, optional JSON geographic data, and validated risk output. Each `user_profiles` row stores a user's usual countries, devices, and login hours as JSON arrays.

`LoginEventRepository` provides event insertion, lookup, paginated per-user history, prior-event lookup, distinct-user queries, and failed user/device-pair queries by IP/time window; `UserProfileRepository` loads and saves profiles. Repository methods flush changes, while the caller owns the session transaction and commit. Login evaluation commits its stored result after computing the score.

`FailedAttemptCounter` stores per-user counters in Redis with a configurable fixed-window TTL. User identifiers are hashed in Redis keys; the counter sets the expiry atomically on the first failure in each window. Separate window lengths use separate counters. A Redis server must be available when these counters are used. Login evaluation currently uses stored events for brute-force and credential-stuffing signals and does not depend on Redis.

`FailedAttemptVelocity` separately records individual failures in per-user Redis sorted sets and atomically returns rolling counts for the inclusive last 1, 5, and 60 minutes. User IDs are hashed; each write prunes entries older than one hour and refreshes the set's one-hour TTL. It remains a standalone helper; login evaluation uses persisted event history for the current rules.

`HighRiskIPList` matches IPv4/IPv6 addresses against the configured `HIGH_RISK_IP_NETWORKS` list. No VPN, Tor, proxy, or other reputation feed is bundled; operators must supply and maintain a trusted list.

## Rule engine

Rules receive an immutable `RuleContext` containing precomputed login signals. Each rule has a unique name, an integer weight from 0 to 100, and a condition; `RuleRegistry` evaluates rules in registration order and returns the matches. `ImpossibleTravelRule` triggers strictly above 900 km/h with weight 40. `BruteForceRule` triggers at five consecutive failures, or when at least five distinct users and five distinct devices have failed from the same IP within `CREDENTIAL_STUFFING_WINDOW_SECONDS` (default 300), with weight 60. Successful logins do not count toward the shared-IP condition, reducing false positives on office, campus, and household networks. The API reports `credential_stuffing_multiple_users_and_devices` for that condition; if both brute-force conditions match, the rule's 60-point weight is still counted only once. `UserAgentProfileChangeRule` adds 15 points when at least two known User-Agent dimensions change on a trusted, previously seen device; it does not duplicate new-device risk. `NewDeviceAndCountryRule` triggers only when both signals are true, with weight 30. `HighRiskIPRule` triggers on a supplied high-risk IP match, with weight 40. `UnusualHourRule` triggers at a six-hour or greater deviation from a user's usual UTC login hours, with weight 15.

`aggregate_score` sums the weights of triggered rules and caps the score at 100. `score_to_decision` uses `ALLOW_MAX_SCORE` and `CHALLENGE_MAX_SCORE`, defaulting to `0–39 → allow`, `40–78 → challenge`, and `79–100 → deny`. Both threshold values are validated at startup and can be overridden with environment variables. Login evaluation builds rule context from saved event history, user profiles, and configured GeoIP/reputation sources, then stores the evaluation result.

`SHADOW_MODE=true` is the safe default for an authentication service integrating this API. This service always returns its calculated score, decision, and reasons; it does not itself block or authenticate logins. The setting does not change the response, and setting it to `false` alone does not add enforcement. A downstream authentication service must decide whether to act on the returned recommendation.

## API

Implemented endpoints:

| Method | Path | Purpose | Plan step |
|---|---|---|---|
| `GET` | `/health` | Health check (`{"status":"ok"}`) | 1.1 — implemented |
| `GET` | `/metrics` | Prometheus request count, latency, and login-decision metrics; no API key required | 6.3 — implemented |
| `GET` | `/demo` | Local browser page for submitting test login events | 4.8 — implemented |
| `POST` | `/v1/login-events/evaluate` | Evaluate and store a login event with risk score, decision, and reasons; requires `X-API-Key` | 1.4–1.5, 4.8 — implemented |
| `POST` | `/v1/feedback` | Label an evaluated event `real_attack` or `false_positive`; requires `X-API-Key`; one label per event | 6.1 — implemented |
| `GET` | `/v1/users/{user_id}/risk-history` | Paginated risk history without IP, device, or user-agent fields; requires `X-API-Key` | 6.4 — implemented |

Set `API_KEY` in the environment or `.env`, then include it in the `X-API-Key` request header. The health, demo, and metrics endpoints are public; evaluation, feedback, and risk-history requests require the key and receive `401 Unauthorized` when it is missing or incorrect. Request timestamps must include a timezone. Apply the SQLite migration with `alembic upgrade head` before using persisted endpoints. GeoIP lookup is disabled by default; enable it only after configuring a valid database path. Each evaluation is saved to `login_events`. A successful `allow` evaluation updates the user's usual device, available country, and UTC login hour only when there is no model anomaly or risk reason other than the low-weight new-device-and-country signal; failed or riskier logins do not update the profile.
Set `RATE_LIMIT_ENABLED=true` to limit authenticated routes using the shared Redis backend. The fixed window allows the configured number of requests, returns `429 Too Many Requests` with `Retry-After` when exceeded, and returns `503 Service Unavailable` rather than bypassing limits if Redis is unavailable. Invalid API keys are rejected before consuming a rate-limit slot.
Submit feedback using the `event_id` returned by login evaluation. The API accepts `real_attack` or `false_positive`, returns `404` for unknown events, and returns `409` if feedback already exists for that event.
Risk history is ordered newest first and accepts `limit` (default 20, maximum 100) and `offset` (default 0); entries expose the event ID, timestamp, risk score, decision, and reasons, but omit login IPs and device identifiers.
Each response includes a generated `X-Request-ID`; the server logs the method, matched route template, status, duration, and request ID as a JSON object without logging request bodies, user IDs in dynamic paths, or authentication headers. Prometheus metrics use the same route-template labels rather than raw paths, and decision metrics use only the bounded `allow`, `challenge`, and `deny` values.

Feedback request:

```json
{
  "event_id": "evt_0123456789abcdef0123456789abcdef",
  "label": "false_positive"
}
```

Risk-history requests may pass `limit` and `offset` as query parameters, for example `/v1/users/u_123/risk-history?limit=20&offset=0`.

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
  "event_id": "evt_0123456789abcdef0123456789abcdef",
  "risk_score": 0,
  "decision": "allow",
  "reasons": []
}
```

The response contains the weighted rule result. Default thresholds are `0–39 → allow`, `40–78 → challenge`, and `79–100 → deny`. These decisions are recommendations only; the API does not enforce them. The OpenAPI page includes example request and response schemas.

### Local test page

After applying migrations and starting the API, open `http://127.0.0.1:8000/demo`, enter the configured API key, and submit an event. Uncheck **Login succeeded** and submit five attempts for the same user to exercise the brute-force rule. The page refreshes its UTC timestamp on each submission and displays the actual API response. It keeps the key in page memory only and sends it to the same origin; use it for local development, not shared or production browsers.

## Model training

Generate training data, train an Isolation Forest using only normal rows, then evaluate against a separate labeled dataset:

```powershell
python scripts/generate_synthetic_data.py --output .\data\synthetic-login-events.csv --normal-count 1000 --suspicious-count 100 --seed 42
python scripts/train.py --input .\data\synthetic-login-events.csv --output .\artifacts\model.joblib --seed 42
python scripts/generate_synthetic_data.py --output .\data\evaluation-login-events.csv --normal-count 500 --suspicious-count 100 --seed 43
python scripts/evaluate.py --input .\data\evaluation-login-events.csv --model-path .\artifacts\model.joblib --output .\artifacts\evaluation.json
```

The generated dataset contains no real users, IP addresses, or credentials and is written under the git-ignored `data/` directory by default. Training requires `scikit-learn`, defaults to 100 estimators and 2% contamination, and uses `MODEL_PATH` as the base path for versioned artifacts, metadata, and the latest-version manifest. Use a different seed and file for evaluation data to avoid evaluating on training examples. The JSON report includes precision, recall, ROC-AUC, false-positive rate, sample count, and model version. Synthetic results measure only the generated distributions and do not establish real-world model performance.

`InferenceService` loads the registered Isolation Forest and returns a bounded anomaly risk score from its decision function; this score is not a probability. Its shared-IP identity-diversity feature uses the lower of the distinct failed-user and failed-device counts, so successful shared-IP activity and repeated failures from just one account or device do not activate that feature. Registered metadata records `feature_schema_version`; inference requires an exact match with the current schema. Metadata without a version is treated as legacy version 1 and rejected by the current version 2 inference code. Legacy models are not automatically retrained or replaced; train and register a compatible model before enabling ML. Login evaluation remains rule-only unless `ML_ENABLED=true`; when enabled it combines 60% rule score with 40% model score. A missing or invalid registered model is surfaced rather than silently falling back to rule-only scoring.

## Tests and quality checks

Run the API test suite and configured quality checks from the repository root:

```powershell
pytest --cov=app --cov-report=term-missing --cov-fail-under=80 -q
ruff check .
mypy app
pre-commit run --all-files
```

The development extra installs pytest-cov and the test dependencies. The configured coverage command enforces the project plan's 80% line-coverage target for `app/`. GeoIP unit tests stub the database reader and do not require a GeoLite2 file; user-agent parsing tests use local parser data and make no network requests. Repository and API tests apply Alembic migrations to isolated temporary SQLite databases. Rule tests cover each condition's boundaries, score aggregation, decision thresholds, history windows, authentication, and API responses. The pre-commit hooks run TOML/YAML and whitespace checks, Ruff lint/format, and mypy.

The clean editable installation, Alembic migration, documented model workflow, and local API endpoints were verified with Python 3.14. The final test suite passes 156 tests; Ruff, mypy, and pre-commit pass. Python 3.12 is the configured CI version but was not installed in the local environment.

GitHub Actions runs Ruff lint and formatting checks, mypy, and pytest on Python 3.12 for pushes and pull requests targeting `main`.

The Security workflow runs `pip-audit` against the installed runtime and development dependencies and scans full Git history with Gitleaks on pushes, pull requests, and a weekly schedule. For repositories owned by a GitHub organization, configure `GITLEAKS_LICENSE` as a repository or organization secret if required by the Gitleaks Action.

## Project structure

Key files and folders:

```text
.
├── .github/workflows/
│   ├── ci.yml
│   ├── publish-container.yml
│   └── security.yml
├── .dockerignore
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── Dockerfile
├── alembic.ini
├── alembic/
├── compose.yaml
├── app/
├── docs/architecture.md
├── PLAN.md
├── README.md
├── pyproject.toml
├── scripts/
└── tests/
```

`app/` contains the service, database layer, rules, and model utilities; `alembic/` contains database migrations; `scripts/` contains the synthetic-data and model CLIs; and `tests/` contains API, feature, and data-layer tests.

## Troubleshooting

- **Cannot start the API:** install the project with `python -m pip install -e ".[dev]"` and run `uvicorn app.main:app --reload` from the repository root.
- **`docker compose` is unavailable:** install or start Docker Desktop and confirm Docker Compose v2 is enabled.
- **Evaluation requests return 503:** set a non-empty `API_KEY` in the environment or `.env`; the service fails closed when authentication is not configured.
- **Evaluation requests fail with a database error:** run `alembic upgrade head` before starting the API.
- **Redis connection errors:** start Redis at the configured `REDIS_URL` before using standalone counter helpers or enabling API-key rate limiting. Rate limiting returns `503` rather than bypassing limits when Redis is unavailable.
- **ML-enabled evaluation fails:** generate data and train a model, then check the versioned files and manifest under `MODEL_PATH`; leave `ML_ENABLED=false` for rule-only behavior. Use a separately generated labeled dataset with `scripts/evaluate.py` to inspect model metrics.

## Privacy and security

API keys come from environment configuration and are not logged. Request logs exclude bodies and authentication headers, and risk-history responses omit IP addresses, device IDs, and user agents. The database does store those raw login-event fields; restrict database access and define encryption, retention, and deletion policies before production use. Decisions are recommendations only, and this API does not enforce `deny` responses.
