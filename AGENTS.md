# Agent Project Memory

## Project Summary

Suspicious Login Detection API: a FastAPI service that evaluates login events and returns a risk score, decision, and reasons. The project plan is in [PLAN.md](./PLAN.md), and setup instructions will be maintained in [README.md](./README.md).

## Current Status

- **Current phase:** Phase 3 — Feature Engineering
- **Latest tag:** `v0.2.0`
- **Current step:** 3.9 — update GeoIP setup documentation
- **Blockers:** GeoLite2 lookups require a locally obtained City database at `GEOIP_DB_PATH`; setup instructions are planned for step 3.9. Risk scoring remains planned for Phase 4.

## Coding Conventions

- Use Python 3.12 and the stack specified in `PLAN.md`.
- Follow Conventional Commits (`type(scope): short description`) when Git is initialized.
- Keep each planned step small and independently revertible.
- Read and update this file and `PLAN.md` as required by the plan; keep `README.md` aligned with implemented behavior.
- Never put credentials, keys, or tokens in source code, logs, or documentation.
- Prefer tests and quality checks specified by the project plan; report actual results.

## Folder Structure

- `app/` — FastAPI service, settings, database session, and ORM models
- `app/db/models.py` — SQLAlchemy models for stored login data
- `app/db/repositories.py` — transaction-aware data-access classes
- `app/redis_counters.py` — Redis-backed failed-attempt counters
- `app/geoip.py` — GeoLite2 IP-to-location lookup
- `app/user_agent.py` — browser, OS, and device classification
- `app/features.py` — standalone login feature calculations
- `app/ip_reputation.py` — supplied IPv4/IPv6 high-risk IP and CIDR matcher
- `alembic/` — schema migration environment and revisions
- `tests/` — API and data-layer tests
- `tests/test_geoip.py` — GeoLite2 lookup unit tests using a stub reader
- `tests/test_user_agent.py` — user-agent parsing and device-class tests
- `tests/test_features.py` — travel-speed and feature-calculation tests
- `tests/test_ip_reputation.py` — high-risk IP/CIDR membership tests
- `scripts/` — maintenance and model scripts
- `docs/` — supplementary documentation
- Root — project metadata, environment template, license, plan, and setup guides

## Common Commands

From the activated project virtual environment, install the project with `python -m pip install -e ".[dev]"`, apply database migrations with `alembic upgrade head`, start the API with `uvicorn app.main:app --reload`, and run `pytest -q`, `ruff check .`, `mypy app`, and `pre-commit run --all-files`.

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
| 2026-11-25 | Store Redis failed-attempt counters under hashed user IDs and set each fixed-window TTL atomically on its first increment. | This avoids exposing raw identifiers in Redis keys and keeps window expiry stable as additional failures arrive. |
| 2026-11-25 | Use MaxMind's `geoip2` reader with the configured GeoLite2 City database; return `None` for addresses without records and surface database/configuration errors. | Callers can distinguish an unlisted address from a broken or missing database without the lookup silently hiding operational failures. |
| 2026-11-25 | Use the `user-agents` parser for browser/OS families and prioritize bot, tablet, mobile, then desktop device classes. | The feature output is stable and typed, while unknown user-agent strings remain representable as `Other`/`other`. |
| 2026-11-25 | Calculate travel speed using Haversine distance (mean Earth radius 6371.0088 km), timezone-aware increasing timestamps, and return no speed when coordinates are unavailable. | These rules make the result reproducible and prevent invalid timestamps or missing GeoIP data from becoming misleading velocity values. |
| 2026-11-25 | Treat a missing profile as empty history for device/country novelty; compare opaque device IDs exactly and country codes case-insensitively; missing country data is not a new-country signal. | New-account signals remain explicit without treating unavailable GeoIP as evidence of novelty. |
| 2026-11-25 | Compare login-hour profiles in UTC and calculate distance to the nearest usual hour on a circular 24-hour clock. | The profile schema has no timezone field, so UTC provides a consistent basis for both observed login hours and feature evaluation. |
| 2026-11-25 | Store rolling failure events in hashed Redis sorted sets, use inclusive 1/5/60-minute score windows, and expire the set after one hour. | Sorted sets preserve event timestamps for genuine rolling counts, unlike the existing fixed-window counter; Lua keeps writes and multi-window reads atomic. |
| 2026-11-25 | Make IP reputation matching accept a caller-supplied IPv4/IPv6 address/CIDR list and ship no reputation feed. | No trusted VPN/Tor/proxy source or update policy is specified, so the matcher stays reusable without embedding stale or unverified classifications. |

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
| 2026-11-25 | Copilot SDK | `feat(db): add SQLAlchemy + Alembic setup` | Added synchronous SQLAlchemy engine/session helpers and Alembic migration configuration using `DATABASE_URL`. | `app/db/`, `alembic/`, `alembic.ini`, `pyproject.toml`, `README.md`, `AGENTS.md`, `PLAN.md`, `.env.example` | SQLite connection, Alembic connection, Ruff, and mypy passed | SQLite remains the local default; psycopg is installed for PostgreSQL URLs. |
| 2026-11-25 | Copilot SDK | `feat(db): add login_events table` | Added the login event ORM model and initial Alembic migration, including score/decision constraints and a user-timestamp index. | `app/db/models.py`, `alembic/env.py`, `alembic/versions/`, `README.md`, `AGENTS.md`, `PLAN.md` | Migration upgrade/check, valid insert, score constraint, Ruff, and mypy passed | Geo data and reasons use JSON columns; event timestamps are timezone-aware. |
| 2026-11-25 | Copilot SDK | `feat(db): add user_profiles table` | Added the user profile ORM model and migration for usual countries, devices, and login hours. | `app/db/models.py`, `alembic/versions/`, `README.md`, `AGENTS.md`, `PLAN.md` | Migration upgrade/check, profile defaults/persistence, Ruff, and mypy passed | Profile arrays use JSON columns keyed by `user_id`. |
| 2026-11-25 | Copilot SDK | `feat(repo): add repository layer` | Added typed login-event and user-profile repositories with insertion, lookup, pagination, and profile upsert operations. | `app/db/repositories.py`, `README.md`, `AGENTS.md`, `PLAN.md` | Repository runtime checks, Ruff, and mypy passed | Repositories flush but leave commit/rollback to the caller's session transaction. |
| 2026-11-25 | Copilot SDK | `feat(redis): add counters for velocity checks` | Added Redis connection setup and per-user failed-attempt counters with an atomic fixed-window TTL. | `app/redis_counters.py`, `pyproject.toml`, `.pre-commit-config.yaml`, `.env.example`, `README.md`, `AGENTS.md`, `PLAN.md`, `tests/test_redis_counters.py` | Redis counter tests: 4 passed; Ruff and mypy passed | User IDs are SHA-256 hashed in Redis keys; expiry is assigned on the first failure in a window. |
| 2026-11-25 | Copilot SDK | `test(db): add repository tests` | Added temporary-SQLite migration/repository tests for events, profiles, pagination, and database constraints. | `tests/conftest.py`, `tests/test_repositories.py`, `AGENTS.md`, `PLAN.md` | `pytest -q`: 16 passed; Ruff, mypy, pre-commit, and Alembic check passed | Each repository test applies the Alembic head to its own temporary database. |
| 2026-11-25 | Copilot SDK | `docs: update README (migrations, DB/Redis) and AGENTS` | Documented the SQLite/PostgreSQL setup, Alembic migrations, repositories, Redis counter TTL, tests, and current Phase 2 status; normalized an import order flagged by Ruff. | `README.md`, `AGENTS.md`, `PLAN.md`, `tests/conftest.py` | Documentation reviewed against implementation; all checks passed | SQLite migrations and repository tests are verified; PostgreSQL connectivity has not been exercised. |
| 2026-11-25 | Copilot SDK | `feat(geo): integrate GeoLite2` | Added a typed MaxMind City lookup using `GEOIP_DB_PATH`, with explicit handling for unlisted addresses and no silent database-error fallback; configured the isolated mypy hook and aligned Ruff versions, including import normalization. | `app/geoip.py`, `pyproject.toml`, `.pre-commit-config.yaml`, `tests/test_geoip.py`, `tests/conftest.py`, `README.md`, `AGENTS.md`, `PLAN.md` | `pytest -q`: 20 passed; Ruff, mypy, pre-commit, and Pylance diagnostics pass | GeoLite2 City database files are not included; README setup details are scheduled for step 3.9. |
| 2026-11-25 | Copilot SDK | `feat(features): add user-agent parsing` | Added a typed user-agent helper for browser/OS families and bot/tablet/mobile/desktop classification with explicit empty-input validation. | `app/user_agent.py`, `pyproject.toml`, `.pre-commit-config.yaml`, `tests/test_user_agent.py`, `README.md`, `AGENTS.md`, `PLAN.md` | User-agent tests: 7 passed; Ruff, mypy, and Pylance diagnostics pass | Parser output was verified for desktop, phone, tablet, bot, and unknown user-agent strings. |
| 2026-11-25 | Copilot SDK | `feat(features): add impossible-travel feature` | Added timezone-aware Haversine travel-speed calculation with explicit handling for missing coordinates, invalid ranges, and non-positive durations. | `app/features.py`, `tests/test_features.py`, `README.md`, `AGENTS.md`, `PLAN.md` | Impossible-travel tests: 9 passed; Ruff and mypy passed | Dateline crossing and equatorial distance cases verify the shortest geographic path and km/h output. |
| 2026-11-25 | Copilot SDK | `feat(features): add new device / new country flags` | Added profile comparisons for unseen device IDs and ISO country codes, including missing-profile and missing-country semantics. | `app/features.py`, `tests/test_features.py`, `README.md`, `AGENTS.md`, `PLAN.md` | Feature tests: 14 passed; Ruff, mypy, and Pylance diagnostics pass | Device IDs are opaque and match exactly; country codes are normalized case-insensitively. |
| 2026-11-25 | Copilot SDK | `feat(features): add time-of-day deviation` | Added UTC-normalized comparison with usual login hours using nearest circular 24-hour distance. | `app/features.py`, `tests/test_features.py`, `README.md`, `AGENTS.md`, `PLAN.md` | Feature tests: 21 passed; Ruff, mypy, and Pylance diagnostics pass | Empty histories return no deviation; naive timestamps and hours outside 0–23 are rejected. |
| 2026-11-25 | Copilot SDK | `feat(features): add failed-attempt velocity` | Added atomic Redis sorted-set recording and rolling counts for the prior 1, 5, and 60 minutes, with hashed user keys and one-hour cleanup. | `app/redis_counters.py`, `tests/test_redis_counters.py`, `README.md`, `AGENTS.md`, `PLAN.md` | Redis counter tests: 8 passed; Ruff, mypy, and Pylance diagnostics pass | Boundaries are inclusive; duplicate failures at the same timestamp are preserved as distinct events. |
| 2026-11-25 | Copilot SDK | `feat(features): add IP reputation (VPN/Tor/proxy list)` | Added IPv4/IPv6 IP and CIDR membership checks against caller-supplied high-risk networks. | `app/ip_reputation.py`, `tests/test_ip_reputation.py`, `README.md`, `AGENTS.md`, `PLAN.md` | IP reputation tests: 4 passed; Ruff, mypy, and Pylance diagnostics pass | No external or built-in reputation list is bundled; list lifecycle remains with the caller. |
| 2026-11-25 | Copilot SDK | `test(features): add unit tests for each feature` | Expanded edge coverage for configured GeoLite2 paths, zero-distance travel, inclusive velocity-window cleanup/TTL, and the complete feature test matrix. | `tests/test_geoip.py`, `tests/test_features.py`, `tests/test_redis_counters.py`, `AGENTS.md`, `PLAN.md` | `pytest -q`: 58 passed; Ruff, mypy, and pre-commit passed | Feature tests cover GeoIP, user agents, travel speed, profile comparisons, time deviation, Redis rolling counts, and IP/CIDR reputation. Pylance shows only the existing unused `event` warning in `app/main.py`. |

## Open Questions

- None currently. Record questions here when a planned requirement needs user clarification.
