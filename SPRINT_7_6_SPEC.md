# Sprint 7.6 — Test Harness & CI Reliability (LOCK CANDIDATE)

## Goal
Make the Invyra AI Review Engine **testable and CI-safe** so every build can be validated with one command, without "random" port failures or import-path issues.

## Scope
### A) CI smoke runner becomes self-contained
- A single command starts the server, waits until healthy, runs smoke requests, and stops the server.
- Works on Windows + Linux in GitHub Actions.

### B) Port discovery is deterministic
- Server writes chosen port to `.invyra_port`.
- Smoke runner reads `.invyra_port`.
- Fallback: probe `8080..8090` if the port file is missing.

### C) Contract smoke coverage (review-only)
Smoke verifies these endpoints:
- `GET /health` returns 200 and JSON with ok status.
- `GET /ai/status` returns 200 and includes `decision_mode`.
- `GET /review/bundle` returns 200 and includes: `ai_status`, `deterministic_patterns`, `ai_explanation`.
- `GET /patterns/day` returns 200 when auth ok.
- Negative auth check returns 401 on at least one protected endpoint when key is wrong.

### D) CI workflow
- GitHub Actions runs on `windows-latest` and `ubuntu-latest`.
- Uses `python -m tools.ci_smoke`.

## Non-goals
- No change to business logic or AI enablement.
- No external provider calls.

## Acceptance criteria
- `run_smoke_tests_sprint7_6.bat` passes on a developer machine even when port 8080 is already in use.
- GitHub Actions job passes on Windows and Ubuntu.
- Smoke output prints target base URL and a clear PASS/FAIL summary.

## Risks & mitigations
- Port file not written fast enough → runner waits briefly and falls back to probing.
- Process cleanup on Windows → runner terminates process and waits; CI uses job teardown as backup.
