# Suspicious Login Detection API

> **Project status:** Setup is in progress. The Python project metadata and environment template now exist, but the API, runtime dependencies, and deployment files have not been created. The implementation sequence is tracked in [PLAN.md](./PLAN.md).

## Overview

The planned service evaluates login attempts and returns a risk score from 0 to 100, a decision (`allow`, `challenge`, or `deny`), and explanatory reasons. The design combines deterministic rules with an Isolation Forest anomaly-detection model.

Planned capabilities include:

- FastAPI login-event evaluation API
- API-key authentication and request-id structured logging
- Behavioral event storage and Redis velocity counters
- GeoIP and login behavior features
- Explainable rule scoring and machine-learning anomaly scoring
- Feedback and monitoring endpoints

These features are not implemented yet.

## Prerequisites

For the planned application:

- Python 3.12
- Docker and Docker Compose for the planned containerized deployment
- PostgreSQL and Redis for the planned production-style local stack; SQLite is planned for development

Only Python is needed for the current skeleton. The service cannot be run yet.

## Installation

### Manual installation

The project targets Python 3.12 or newer. From the repository root, create and activate a virtual environment, then install the development tooling:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The API and runtime dependencies are not implemented yet, so there is no service start command.

Configuration names and safe local defaults are listed in [.env.example](./.env.example). Copy that file to `.env` and set a private `API_KEY` only when configuring a local environment. Never commit `.env` or real credentials.

### Docker installation

Docker support is planned for Phase 7. The `Dockerfile` and Compose configuration do not exist yet, so there is no working Docker install command.

## Configuration

The environment template is [.env.example](./.env.example). These names are planned configuration and are not read by an application yet:

| Variable | Purpose | Status |
|---|---|---|
| `DATABASE_URL` | Database connection string | Planned in Phase 2 |
| `REDIS_URL` | Redis connection string | Planned in Phase 2 |
| `GEOIP_DB_PATH` | Path to the GeoLite2 database | Planned in Phase 3 |
| `SHADOW_MODE` | Evaluate decisions without enforcing them | Planned in Phase 4 |
| `MODEL_PATH` | Location of the trained model artifact | Planned in Phase 5 |
| `API_KEY` | API-key authentication secret | Planned for Phase 1; keep the value private |

Threshold settings are also planned to be configurable, but their environment variable names have not been specified. They will be defined with the settings implementation.

## API

No endpoints are implemented yet. Planned core endpoints:

| Method | Path | Purpose | Planned step |
|---|---|---|---|
| `GET` | `/health` | Health check | 1.1 |
| `POST` | `/v1/login-events/evaluate` | Evaluate a login event | 1.4 |
| `POST` | `/v1/feedback` | Submit a feedback label | 6.1 |
| `GET` | `/v1/users/{id}/risk-history` | Retrieve a user's risk history | 6.4 |

The example below records the target request and response shape from the plan. It is not callable until the API is implemented.

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

Example response:

```json
{
  "event_id": "evt_001",
  "risk_score": 78,
  "decision": "challenge",
  "reasons": ["impossible_travel", "new_device"]
}
```

The example is illustrative; the endpoint's real response will be documented after its schema is implemented.

The clarified default thresholds are `0–39 → allow`, `40–78 → challenge`, and `79–100 → deny`, so this example is consistent. These are planned defaults; scoring is not implemented yet.

## Model training

Model training and evaluation are planned for Phase 5. The training script is planned at `scripts/train.py`; neither it nor the model artifacts exist yet. Training, inference, and evaluation commands will be added once implemented and tested.

## Tests and quality checks

Run the configured quality checks from the repository root:

```powershell
ruff check .
mypy app
pre-commit run --all-files
```

The pre-commit hooks run TOML/YAML and whitespace checks, Ruff lint/format, and mypy. `pytest -q` is planned, but the test suite and pytest dependency have not been added yet.

## Project structure

Current files:

```text
.
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── AGENTS.md
├── app/
│   └── __init__.py
├── docs/
├── LICENSE
├── PLAN.md
├── README.md
├── pyproject.toml
├── scripts/
└── tests/
```

`app/` will contain the service, `tests/` automated tests, `scripts/` model and maintenance scripts, and `docs/` supplementary documentation.

## Troubleshooting

- **Cannot start the API:** expected at this stage; application code and runtime dependencies are not present yet.
- **Docker Compose files not found:** Docker support is planned for Phase 7 and has not been added.
- **Environment variable has no effect:** there is no settings implementation yet. Check the configuration table above for planned variables.
- **A documented command fails:** the quality and model commands are plans, not verified commands. They will be checked when their implementation steps are reached.

## Privacy and security

The plan calls for API keys to come from environment configuration and never be logged. IP addresses and device IDs should be hashed or masked where possible, and retention and user-data deletion requirements should be addressed before production use. Deny decisions should initially run in shadow mode to measure false positives.
