# Agent Project Memory

## Project Summary

Suspicious Login Detection API: a FastAPI service that evaluates login events and returns a risk score, decision, and reasons. The project plan is in [PLAN.md](./PLAN.md), and setup instructions will be maintained in [README.md](./README.md).

## Current Status

- **Current phase:** Phase 0 — Setup and Documentation
- **Latest tag:** None
- **Current step:** 0.3 — repository metadata and Python project configuration remain to be added
- **Blockers:** Application code, package configuration, and project tooling are not present yet.

## Coding Conventions

- Use Python 3.12 and the stack specified in `PLAN.md`.
- Follow Conventional Commits (`type(scope): short description`) when Git is initialized.
- Keep each planned step small and independently revertible.
- Read and update this file and `PLAN.md` as required by the plan; keep `README.md` aligned with implemented behavior.
- Never put credentials, keys, or tokens in source code, logs, or documentation.
- Prefer tests and quality checks specified by the project plan; report actual results.

## Folder Structure

The workspace currently contains `PLAN.md`, `AGENTS.md`, and `README.md`. The intended structure includes:

- `app/` — application code
- `tests/` — automated tests
- `scripts/` — maintenance and model scripts
- `docs/` — supplementary documentation

## Common Commands

Commands will be documented here and in `README.md` when the project tooling is established. Planned checks include `pytest -q`, `ruff check .`, and `mypy app`; they have not been run because the project skeleton and tooling do not exist yet.

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

## Work Log

| Date | Agent | Commit | Work done | Files changed | Test status | Notes |
|---|---|---|---|---|---|---|
| 2026-11-25 | Copilot SDK | Not committed | Created the initial project memory file for step 0.1. | `AGENTS.md`, `PLAN.md` | Not run (documentation-only step) | Git operations are unavailable until step 0.3 initializes the repository. |
| 2026-11-25 | Copilot SDK | Not committed | Created the initial setup and usage guide for step 0.2. | `README.md`, `AGENTS.md`, `PLAN.md` | Not run (documentation-only step) | Commands and features are labeled planned where implementation does not exist. Git is initialized but has no commits. |
| 2026-11-25 | Copilot SDK | Not committed | Resolved the score-78 decision mismatch and aligned the documented default ranges. | `README.md`, `AGENTS.md`, `PLAN.md` | Not run (documentation-only clarification) | User selected the sample behavior; defaults now use 40–78 for `challenge`. |
| 2026-11-25 | Copilot SDK | `docs: create AGENTS.md memory file` | Committed the project memory file for step 0.1. | `AGENTS.md`, `PLAN.md` | Not run (documentation-only step) | Step 0.2 remains prepared and uncommitted. |
| 2026-11-25 | Copilot SDK | `docs: create README.md install guide` | Committed the installation and usage guide for step 0.2. | `README.md`, `AGENTS.md`, `PLAN.md` | Not run (documentation-only step) | No application or setup commands are claimed to work before implementation. |

## Open Questions

- None currently. Record questions here when a planned requirement needs user clarification.
