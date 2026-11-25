# Project Plan: Suspicious Login Detection API

An API service that returns a **risk score (0–100)** and a **decision** (`allow` / `challenge` / `deny`) for every login attempt. It combines deterministic rules with a machine-learning anomaly-detection model.

---

## 🤖 Mandatory Instructions for the AI Agent

> This is the most important section of the file. Every agent (Claude, Cursor, Copilot, etc.) working on this project **must read and follow this section before doing anything else**.

### A) Initial creation of documentation files (the agent's first task)
If any of the files below do not exist in the project root, the agent must create them **before writing any code**:

1. **`AGENTS.md`**: the project memory file. It must contain:
   - Project summary and links to `PLAN.md` and `README.md`
   - Current status (current phase, latest tag, blockers)
   - Coding conventions, folder structure, and common commands
   - Agent working rules
   - Architecture Decision Log (table)
   - **Work Log** (table of everything the AI has done)
   - Open questions
2. **`README.md`**: the installation and setup guide. It must contain:
   - Overview and features
   - Prerequisites
   - Docker install and manual install
   - Environment variables table (`.env`)
   - Example API request and response
   - Endpoint list
   - Model training, running tests, and quality checks
   - Project structure and troubleshooting
3. **`.env.example`**: every environment variable, with no real values.

### B) Update rule after every commit
After **every commit or step**, the agent must:

1. **`AGENTS.md`**
   - Append a new row to the end of the Work Log table (date, agent name, commit number, work done, files changed, test status, notes).
   - Update the "Current Status" section.
   - Record any architectural decision in the Decision Log.
   - **Never delete or edit previous rows.**
2. **`README.md`**
   - If a new endpoint, environment variable, install command, or dependency was added, reflect it immediately.
   - At the end of each phase, actually run the README commands once and confirm they work.
3. **`PLAN.md`**: mark the completed commit with ✅ in the phase table.

### C) End-of-phase checklist (Definition of Done)
The agent may declare a phase "done" only if all of the following are true:

- [ ] All commits in the phase are completed and marked ✅
- [ ] `pytest -q` passes
- [ ] `ruff check .` and `mypy app` pass
- [ ] `AGENTS.md` is up to date (Work Log + Current Status)
- [ ] `README.md` matches the real state of the project
- [ ] A version tag is created (`v0.X.0`)

### D) Behavioral rules
- Do only the **next commit/phase**. Skipping ahead is forbidden.
- One commit = one small, revertible task.
- Do not guess. Write ambiguities under "Open Questions" in `AGENTS.md` and ask the user.
- Never write keys, passwords, or tokens in code, logs, or docs.
- Report real test results. If something fails, do not hide it.

---

## Proposed Stack

| Area | Choice |
|---|---|
| Language / framework | Python 3.12 + FastAPI |
| Database | PostgreSQL (SQLite in development) |
| Cache / counters | Redis |
| ML model | scikit-learn (IsolationForest) |
| GeoIP | MaxMind GeoLite2 |
| Testing | pytest + httpx |
| Code quality | ruff + mypy + pre-commit |
| Deployment | Docker + docker-compose + GitHub Actions |

## Commit Convention (Conventional Commits)

Format: `type(scope): short description`

- `feat` new feature, `fix` bug fix, `docs` documentation, `test` tests, `refactor` refactoring, `chore` tooling/config, `ci` pipeline.
- Every commit is an independent, revertible unit of work.
- Documentation touched by a change (`AGENTS.md`, `README.md`) is updated **in the same commit** or immediately in the next `docs` commit.
- Tag after each phase: `v0.1.0`, `v0.2.0`, ...

## High-Level Architecture

```
Client/Auth-Service ──► POST /v1/login-events/evaluate
                             │
                    ┌────────▼─────────┐
                    │  Feature Builder │ ← GeoIP, Redis counters, User profile (DB)
                    └────────┬─────────┘
              ┌──────────────┴──────────────┐
      ┌───────▼───────┐             ┌───────▼───────┐
      │  Rule Engine  │             │   ML Model    │
      └───────┬───────┘             └───────┬───────┘
              └──────────────┬──────────────┘
                     ┌───────▼────────┐
                     │ Risk Aggregator│ → score + decision + reasons
                     └────────────────┘
```

---

## Phase 0: Setup and Documentation
**Goal:** a clean project skeleton, code-quality tooling, and the `AGENTS.md` and `README.md` files.

| # | Commit | Description | Status |
|---|---|---|---|
| 0.1 | `docs: create AGENTS.md memory file` | **The agent creates `AGENTS.md` per section (A)** and logs the first Work Log row | ✅ |
| 0.2 | `docs: create README.md install guide` | **The agent creates `README.md` per section (A)** (install guide, env vars, API example) | ✅ |
| 0.3 | `chore: init repository` | Repo, `.gitignore`, `LICENSE`, `pyproject.toml`, `.env.example` | ✅ |
| 0.4 | `chore: add project structure` | `app/`, `tests/`, `scripts/`, `docs/` folders | ✅ |
| 0.5 | `chore: add ruff, mypy and pre-commit` | Linter, type checker, pre-commit hooks | ✅ |
| 0.6 | `docs: sync AGENTS.md and README.md with setup` | Align docs with the real project structure | ✅ |

**Done when:** `AGENTS.md`, `README.md`, and `.env.example` exist; `pre-commit run --all-files` passes.

## Phase 1: Core API
**Goal:** the service starts and the main endpoint works with a stub response.

| # | Commit | Description | Status |
|---|---|---|---|
| 1.1 | `feat(api): bootstrap FastAPI app` | `app/main.py`, `GET /health` | ✅ |
| 1.2 | `feat(config): add settings via env vars` | `pydantic-settings`, update `.env.example` | ✅ |
| 1.3 | `feat(schemas): add login event request/response models` | Pydantic models | ✅ |
| 1.4 | `feat(api): add POST /v1/login-events/evaluate (stub)` | Fixed `allow` response | ⬜ |
| 1.5 | `feat(auth): add API key authentication` | `X-API-Key` header | ⬜ |
| 1.6 | `feat(logging): add structured JSON logging + request id` | Structured logs | ⬜ |
| 1.7 | `test(api): add tests for health and evaluate` | Initial tests | ⬜ |
| 1.8 | `docs: update README endpoints and AGENTS work log` | **The agent updates the endpoint list and env vars in README and the status in AGENTS.md** | ⬜ |

**Request (example):**
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
**Response (example):**
```json
{
  "event_id": "evt_001",
  "risk_score": 78,
  "decision": "challenge",
  "reasons": ["impossible_travel", "new_device"]
}
```

## Phase 2: Data Layer
**Goal:** store events and a behavioral profile per user.

| # | Commit | Description | Status |
|---|---|---|---|
| 2.1 | `feat(db): add SQLAlchemy + Alembic setup` | Connection and migrations | ⬜ |
| 2.2 | `feat(db): add login_events table` | user_id, ip, geo, device, ua, ts, score, decision | ⬜ |
| 2.3 | `feat(db): add user_profiles table` | Usual countries, devices, and hours per user | ⬜ |
| 2.4 | `feat(repo): add repository layer` | Data-access classes | ⬜ |
| 2.5 | `feat(redis): add counters for velocity checks` | Failed-attempt counters with TTL | ⬜ |
| 2.6 | `test(db): add repository tests` | Tests with a temporary database | ⬜ |
| 2.7 | `docs: update README (migrations, DB/Redis) and AGENTS` | `alembic upgrade head`, `DATABASE_URL`, `REDIS_URL` | ⬜ |

## Phase 3: Feature Engineering
**Goal:** turn a raw event into usable features.

| # | Commit | Description | Status |
|---|---|---|---|
| 3.1 | `feat(geo): integrate GeoLite2` | IP → country/city/lat/lon | ⬜ |
| 3.2 | `feat(features): add user-agent parsing` | Browser, OS, device type | ⬜ |
| 3.3 | `feat(features): add impossible-travel feature` | Required speed between two logins (km/h) | ⬜ |
| 3.4 | `feat(features): add new device / new country flags` | Compare with the user profile | ⬜ |
| 3.5 | `feat(features): add time-of-day deviation` | Distance from the user's usual hours | ⬜ |
| 3.6 | `feat(features): add failed-attempt velocity` | Failures in the last 1, 5, and 60 minutes | ⬜ |
| 3.7 | `feat(features): add IP reputation (VPN/Tor/proxy list)` | High-risk IP list | ⬜ |
| 3.8 | `test(features): add unit tests for each feature` | One test set per feature | ⬜ |
| 3.9 | `docs: update README (GeoIP setup) and AGENTS` | GeoLite2 download guide and `GEOIP_DB_PATH` | ⬜ |

## Phase 4: Rule Engine
**Goal:** fast, explainable detection that needs no model.

| # | Commit | Description | Status |
|---|---|---|---|
| 4.1 | `feat(rules): add rule base class and registry` | Each rule: name, weight, condition | ⬜ |
| 4.2 | `feat(rules): impossible travel rule` | Speed above 900 km/h | ⬜ |
| 4.3 | `feat(rules): brute force / credential stuffing rule` | Consecutive failures, or one IP across many users | ⬜ |
| 4.4 | `feat(rules): new device + new country rule` | Combination of two signals | ⬜ |
| 4.5 | `feat(rules): high-risk IP rule` | Tor / VPN / proxy | ⬜ |
| 4.6 | `feat(rules): unusual hour rule` | Login at an atypical hour | ⬜ |
| 4.7 | `feat(scoring): aggregate rule scores to 0-100` | Weighted sum capped at 100 | ⬜ |
| 4.8 | `feat(api): return reasons list in response` | Return the reasons for the decision | ⬜ |
| 4.9 | `test(rules): add rule tests and edge cases` | Boundary tests | ⬜ |
| 4.10 | `docs: update README (thresholds, SHADOW_MODE) and AGENTS` | Thresholds and shadow mode | ⬜ |

**Default thresholds:** `0–39 → allow`, `40–78 → challenge` (e.g. OTP), `79–100 → deny`. Configurable via settings. These ranges preserve the example response where a score of 78 is `challenge`.

> 🏷️ **First usable version (MVP):** end of Phase 4 → tag `v0.4.0`

## Phase 5: Machine Learning Model
**Goal:** catch anomalies the rules miss.

| # | Commit | Description | Status |
|---|---|---|---|
| 5.1 | `feat(ml): add synthetic data generator` | Synthetic normal and suspicious data | ⬜ |
| 5.2 | `feat(ml): add training script (IsolationForest)` | `scripts/train.py` | ⬜ |
| 5.3 | `feat(ml): add model registry (versioned artifacts)` | Save models with version and metadata | ⬜ |
| 5.4 | `feat(ml): add inference service` | Load model and compute anomaly score | ⬜ |
| 5.5 | `feat(scoring): blend rules + ML score` | e.g. `0.6 * rules + 0.4 * ml` | ⬜ |
| 5.6 | `feat(ml): add evaluation script` | precision / recall / ROC-AUC | ⬜ |
| 5.7 | `test(ml): add model smoke tests` | Output stays within valid range | ⬜ |
| 5.8 | `docs: update README (train/evaluate) and AGENTS` | Train/evaluate commands and `MODEL_PATH` | ⬜ |

## Phase 6: Feedback and Monitoring
**Goal:** learn from mistakes and observe service health.

| # | Commit | Description | Status |
|---|---|---|---|
| 6.1 | `feat(api): add POST /v1/feedback` | Label: "real attack" / "false positive" | ⬜ |
| 6.2 | `feat(profile): update user profile on trusted logins` | Update profile after a confirmed login | ⬜ |
| 6.3 | `feat(metrics): add Prometheus metrics` | Request count, latency, decision distribution | ⬜ |
| 6.4 | `feat(api): add GET /v1/users/{id}/risk-history` | User risk history | ⬜ |
| 6.5 | `feat(ratelimit): add rate limiting per API key` | Abuse protection | ⬜ |
| 6.6 | `docs: update README endpoints and AGENTS` | New endpoints and `/metrics` | ⬜ |

## Phase 7: Deployment and Hardening
**Goal:** production-ready.

| # | Commit | Description | Status |
|---|---|---|---|
| 7.1 | `chore(docker): add Dockerfile (multi-stage)` | Slim image | ⬜ |
| 7.2 | `chore(docker): add docker-compose (api, postgres, redis)` | Full local stack | ⬜ |
| 7.3 | `ci: add GitHub Actions (lint, type-check, tests)` | CI pipeline | ⬜ |
| 7.4 | `ci: add docker build and push` | Publish the image | ⬜ |
| 7.5 | `docs: add OpenAPI examples and architecture diagram` | API docs | ⬜ |
| 7.6 | `chore(security): add dependency audit and secrets scan` | `pip-audit`, `gitleaks` | ⬜ |
| 7.7 | `docs: final README verification` | **The agent runs every README install step from scratch in a clean environment and confirms it works** | ⬜ |
| 7.8 | `docs: finalize AGENTS.md and release v1.0.0` | Final status, tag `v1.0.0` | ⬜ |

---

## Security and Privacy Notes
- Store IPs and device IDs **hashed or masked** where possible, and define a retention period.
- API keys are read only from environment variables and never logged.
- Treat `deny` as advisory at first and run in shadow mode to measure the false-positive rate before blocking for real.
- Provide a way to delete a user's data to comply with data-protection laws (e.g. GDPR).

## Success Criteria
- Response latency `p95 < 100ms`
- False-positive rate below `2%` on evaluation data
- Test coverage above `80%`
- `AGENTS.md` and `README.md` always match the real state of the code

## Suggested Execution Order
Phase 0 → 1 → 2 → 3 → 4 (MVP) → 5 → 6 → 7.
