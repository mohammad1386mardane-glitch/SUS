# Suspicious Login Detection API

> **Project status:** The FastAPI health endpoint is implemented. Login evaluation and the remaining planned features are still in progress; the implementation sequence is tracked in [PLAN.md](./PLAN.md).

## Overview

The planned service evaluates login attempts and returns a risk score from 0 to 100, a decision (`allow`, `challenge`, or `deny`), and explanatory reasons. The design combines deterministic rules with an Isolation Forest anomaly-detection model.

Planned capabilities include:

- FastAPI login-event evaluation API
- API-key authentication and request-id structured logging
- Behavioral event storage and Redis velocity counters
- GeoIP and login behavior features
- Explainable rule scoring and machine-learning anomaly scoring
- Feedback and monitoring endpoints

The health endpoint is implemented. The other capabilities are planned and not yet available.

## Prerequisites

For the planned application:

- Python 3.12
- Docker and Docker Compose for the planned containerized deployment
- PostgreSQL and Redis for the planned production-style local stack; SQLite is planned for development

Only Python is needed for the current skeleton. The service cannot be run yet.

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
| `DATABASE_URL` | Database connection string | Default: local SQLite URL; database integration planned in Phase 2 |
| `REDIS_URL` | Redis connection string | Default: local Redis URL; Redis integration planned in Phase 2 |
| `GEOIP_DB_PATH` | Path to the GeoLite2 database | Default: `data/GeoLite2-City.mmdb`; GeoIP integration planned in Phase 3 |
| `SHADOW_MODE` | Evaluate decisions without enforcing them | Default: `true`; enforcement behavior planned in Phase 4 |
| `MODEL_PATH` | Location of the trained model artifact | Default: `artifacts/model.joblib`; model support planned in Phase 5 |
| `API_KEY` | API-key authentication secret | Defaults to empty; API-key authentication is planned in step 1.5 |

`API_KEY` is stored as a secret value and is not included in its normal string representation. Do not put a real key in source control.

## API

Implemented and planned core endpoints:

| Method | Path | Purpose | Planned step |
|---|---|---|---|
| `GET` | `/health` | Health check (`{"status":"ok"}`) | 1.1 — implemented |
| `POST` | `/v1/login-events/evaluate` | Evaluate a login event | 1.4 |
| `POST` | `/v1/feedback` | Submit a feedback label | 6.1 |
| `GET` | `/v1/users/{id}/risk-history` | Retrieve a user's risk history | 6.4 |

The login-event request and response schemas are defined. The evaluation endpoint is the next implementation step.

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

The response example is illustrative until the endpoint is implemented.

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

The editable installation and listed quality checks were verified with Python 3.14. The project requires Python 3.12 or newer.

## Project structure

Current files:

```text
.
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── AGENTS.md
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── settings.py
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

- **Cannot start the API:** install the project with `python -m pip install -e ".[dev]"` and run `uvicorn app.main:app --reload` from the repository root.
- **Docker Compose files not found:** Docker support is planned for Phase 7 and has not been added.
- **Environment variable has no effect:** there is no settings implementation yet. Check the configuration table above for planned variables.
- **A documented command fails:** the quality and model commands are plans, not verified commands. They will be checked when their implementation steps are reached.

## Privacy and security

The plan calls for API keys to come from environment configuration and never be logged. IP addresses and device IDs should be hashed or masked where possible, and retention and user-data deletion requirements should be addressed before production use. Deny decisions should initially run in shadow mode to measure false positives.
