# Agent Project Memory

## Project Summary

Suspicious Login Detection API: a FastAPI service that evaluates login events and returns a risk score, decision, and reasons. The project plan is in [PLAN.md](./PLAN.md), and setup instructions will be maintained in [README.md](./README.md).

## Current Status

- **Current phase:** Phase 1 — Core API
- **Latest tag:** `v0.1.0`
- **Current step:** 2.1 — add SQLAlchemy and Alembic setup
- **Blockers:** Risk scoring remains planned for Phase 4; Phase 1's API tests and quality checks pass.

## Coding Conventions

- Use Python 3.12 and the stack specified in `PLAN.md`.
- Follow Conventional Commits (`type(scope): short description`) when Git is initialized.
- Keep each planned step small and independently revertible.
- Read and update this file and `PLAN.md` as required by the plan; keep `README.md` aligned with implemented behavior.
- Never put credentials, keys, or tokens in source code, logs, or documentation.
- Prefer tests and quality checks specified by the project plan; report actual results.

## Folder Structure

- `app/` — application package; service code will be added in Phase 1
- `tests/` — automated tests
- `scripts/` — maintenance and model scripts
- `docs/` — supplementary documentation
- Root — project metadata, environment template, license, plan, and setup guides

## Common Commands

From the activated project virtual environment, install the project with `python -m pip install -e ".[dev]"`, start the API with `uvicorn app.main:app --reload`, and run `pytest -q`, `ruff check .`, `mypy app`, and `pre-commit run --all-files`.

## Agent Working Rules

- Follow the execution order and do only the next planned commit/step.
- Do not guess on ambiguous requirements; record open questions and ask for clarification.
- After each step, update the work log and current status, sync relevant documentation, and update `PLAN.md`.
- Do not claim tests, commits, or tags that were not actually performed.

## Architecture Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-11-25 | Use the stack and high-level architecture specified in `PLAN.md` (FastAPI, PostgreSQL/SQLite, Redis, scikit-learn). | This is the project plan's proposed baseline; details remain subject to the planned implementation steps. |
| 2026-11-25 | Set default decisions to `0–39 allow`, `40–78 challenge`, and `79–100 deny`. | The user chose to preserve the plan's example where a score of 78 is `challenge`; these ranges resolve the conflicting earlier defaults. |
| 2026-11-25 | Use the MIT license and `API_KEY` as the planned API-key environment variable. | The license is a permissive baseline; `API_KEY` gives the previously unnamed setting an explicit placeholder without adding a credential. |
| 2026-11-25 | Require a configured API key for login evaluation, compare keys with `compare_digest`, and keep `/health` public. | Authentication fails closed with `503` when `API_KEY` is unset, preventing an unconfigured service from accidentally accepting evaluations. |

## Work Log

| Date | Agent | Commit | Work done | Files changed | Test status | Notes |
|---|---|---|---|---|---|---|
| 2026-11-25 | Copilot SDK | Not committed | Created the initial project memory file for step 0.1. | `AGENTS.md`, `PLAN.md` | Not run (documentation-only step) | Git operations are unavailable until step 0.3 initializes the repository. |
| 2026-11-25 | Copilot SDK | Not committed | Created the initial setup and usage guide for step 0.2. | `README.md`, `AGENTS.md`, `PLAN.md` | Not run (documentation-only step) | Commands and features are labeled planned where implementation does not exist. Git is initialized but has no commits. |
| 2026-11-25 | Copilot SDK | Not committed | Resolved the score-78 decision mismatch and aligned the documented default ranges. | `README.md`, `AGENTS.md`, `PLAN.md` | Not run (documentation-only clarification) | User selected the sample behavior; defaults now use 40–78 for `challenge`. |
| 2026-11-25 | Copilot SDK | `docs: create AGENTS.md memory file` | Committed the project memory file for step 0.1. | `AGENTS.md`, `PLAN.md` | Not run (documentation-only step) | Step 0.2 remains prepared and uncommitted. |
| 2026-11-25 | Copilot SDK | `docs: create README.md install guide` | Committed the installation and usage guide for step 0.2. | `README.md`, `AGENTS.md`, `PLAN.md` | Not run (documentation-only step) | No application or setup commands are claimed to work before implementation. |
| 2026-11-25 | Copilot SDK | Not committed | Added repository metadata, ignore rules, and the environment template for step 0.3. | `.gitignore`, `LICENSE`, `pyproject.toml`, `.env.example`, `README.md`, `AGENTS.md`, `PLAN.md` | Pending validation | Uses MIT and `API_KEY`; no real credentials are included. |
| 2026-11-25 | Copilot SDK | `chore: init repository` | Committed the repository metadata and environment template for step 0.3. | `.gitignore`, `LICENSE`, `pyproject.toml`, `.env.example`, `README.md`, `AGENTS.md`, `PLAN.md` | Static configuration checks passed | TOML parsed; required environment keys and ignore behavior validated. Application installation and tests are not available yet. |
| 2026-11-25 | Copilot SDK | `chore: add project structure` | Added the planned application, test, script, and documentation directories. | `app/__init__.py`, `tests/.gitkeep`, `scripts/.gitkeep`, `docs/.gitkeep`, `README.md`, `AGENTS.md`, `PLAN.md` | Directory structure verified; no tests exist yet | The `app` package marker supports the package discovery configured in `pyproject.toml`. |
| 2026-11-25 | Copilot SDK | `chore: add ruff, mypy and pre-commit` | Configured Ruff, mypy, and pre-commit for step 0.5. | `pyproject.toml`, `.pre-commit-config.yaml`, `README.md`, `AGENTS.md`, `PLAN.md` | `ruff check .`, `mypy app`, and `pre-commit run --all-files` passed | Pytest remains pending until tests and its dependency are introduced. |
| 2026-11-25 | Copilot SDK | `docs: sync AGENTS.md and README.md with setup` | Synced setup documentation with the verified Python metadata, environment, structure, and quality tooling for step 0.6. | `README.md`, `AGENTS.md`, `PLAN.md` | Editable install and documented quality checks passed on Python 3.14 | Phase acceptance still needs `pytest -q`; no test suite exists yet. |
| 2026-11-25 | Copilot SDK | `feat(api): bootstrap FastAPI app` | Added the FastAPI application and `GET /health` for step 1.1. | `app/main.py`, `pyproject.toml`, `.pre-commit-config.yaml`, `README.md`, `AGENTS.md`, `PLAN.md` | HTTP health check, Ruff, mypy, and pre-commit passed | Added FastAPI to the isolated mypy hook environment; phase 0 tag remains deferred pending tests. |
| 2026-11-25 | Copilot SDK | `feat(config): add settings via env vars` | Added typed settings from environment variables and `.env` for step 1.2. | `app/settings.py`, `pyproject.toml`, `.pre-commit-config.yaml`, `.env.example`, `README.md`, `AGENTS.md`, `PLAN.md` | Settings defaults, `.env` parsing, environment overrides, boolean parsing, secret masking, Ruff, mypy, and pre-commit passed | API keys use `SecretStr`; no real credentials are provided. |
| 2026-11-25 | Copilot SDK | `feat(schemas): add login event request/response models` | Added validated Pydantic request and response schemas for login events. | `app/schemas.py`, `README.md`, `AGENTS.md`, `PLAN.md` | Pending validation | Request IPs are parsed as IPv4 or IPv6; scores are bounded to 0–100. |
| 2026-11-25 | Copilot SDK | `feat(api): secure and instrument login evaluation` | Added the login evaluation stub with API-key authentication and JSON request logging. | `app/main.py`, `app/settings.py`, `.env.example`, `README.md`, `AGENTS.md`, `PLAN.md` | `pytest -q`: 6 passed; Ruff, mypy, and pre-commit passed | Missing or invalid keys receive 401; missing server configuration fails closed with 503. |
| 2026-11-25 | Copilot SDK | `feat(api): secure and instrument login evaluation` | Protected login evaluation with the configured `X-API-Key`; the health endpoint remains public. | `app/main.py`, `app/settings.py`, `.env.example`, `README.md`, `AGENTS.md`, `PLAN.md` | Focused auth checks, Ruff, and mypy passed | Missing or invalid keys receive 401; missing server configuration fails closed with 503. |
| 2026-11-25 | Copilot SDK | `feat(api): secure and instrument login evaluation` | Added JSON request logs and a generated `X-Request-ID` response header. | `app/main.py`, `README.md`, `AGENTS.md`, `PLAN.md` | API tests, Ruff, mypy, and pre-commit passed | Logs include request method, path, status, duration, and request ID; bodies and credentials are excluded. |
| 2026-11-25 | Copilot SDK | `feat(api): secure and instrument login evaluation` | Added API tests for public health, API-key behavior, event validation, stub responses, and JSON request logs. | `tests/test_api.py`, `pyproject.toml`, `AGENTS.md`, `PLAN.md` | `pytest -q`: 6 passed; Ruff, mypy, and pre-commit passed | Added `pytest` and `httpx2` to the development dependencies for Starlette's TestClient. |
| 2026-11-25 | Copilot SDK | `feat(api): secure and instrument login evaluation` | Updated setup, authentication, logging, API, test, and project-status documentation to match the implementation. | `README.md`, `AGENTS.md`, `PLAN.md` | Documentation reviewed against implementation | No separate documentation test is configured. |

## Open Questions

- None currently. Record questions here when a planned requirement needs user clarification.
