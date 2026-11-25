# Agent Project Memory

## Project Summary

Suspicious Login Detection API: a FastAPI service that evaluates login events and returns a risk score, decision, and reasons. The project plan is in [PLAN.md](./PLAN.md), and setup instructions will be maintained in [README.md](./README.md).

## Current Status

- **Current phase:** Phase 0 — Setup and Documentation
- **Latest tag:** None
- **Current step:** Phase 0 acceptance — documentation is synced; `pytest -q` is not yet runnable because tests and the pytest dependency have not been added.
- **Blockers:** The application implementation and tests are not present yet.

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

From the activated project virtual environment, install development tools with `python -m pip install -e ".[dev]"`. Run `ruff check .`, `mypy app`, and `pre-commit run --all-files`. `pytest -q` remains pending until test dependencies and tests are added.

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

## Open Questions

- None currently. Record questions here when a planned requirement needs user clarification.
