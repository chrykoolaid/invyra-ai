# Invyra AI Engine — Sprint 7.7 Spec (LOCK-CANDIDATE)

## Goal
Harden the **test harness + CI smoke contract** so a fresh machine can:
1) start the review server deterministically,
2) run smoke tests against the **bundle endpoint** (authoritative path),
3) validate the **bundle JSON contract** (keys, types, minimal invariants),
4) produce a **single pass/fail outcome** with a clear error reason.

> No AI “actions”. Review-only mode stays locked.

## Non-goals (explicit)
- No model/provider integration
- No write-back actions to Invyra Core
- No schema migrations beyond the test harness contract
- No UI redesign beyond small labels needed to support new contract messages

## Locked behavior (carry-over)
- `decision_mode = review-only` is enforced.
- Kill-switch defaults to disabled; **AI is off** unless explicitly enabled in future work.
- Bundle endpoint remains the recommended path for UI and CI consistency.

## Deliverables
### A) Contracted smoke-test interface
- One entrypoint: `python -m tools.ci_smoke`
- Accepts:
  - `--host` (default 127.0.0.1)
  - `--port` (default 8080; respects auto-bump output from server launcher)
  - `--workspace_id`
  - `--day` and `--compare_to`
  - `--api_key` (optional; if absent use env `INVYRA_AI_INGEST_API_KEY`)
- Outputs:
  - `[OK]` / `[FAIL]` lines with **single root-cause**
  - machine-friendly exit codes: `0=pass`, `2=fail`, `3=infra fail`

### B) Bundle contract validation
Smoke test validates `/review/bundle`:
- Response code 200
- JSON top-level keys:
  - `meta` (dict)
  - `ai_status` (dict)
  - `deterministic_patterns` (dict)
  - `ai_explanation` (dict or null if not available)
- `meta` must include:
  - `schema_version` (string)
  - `engine_version` (string)
- `deterministic_patterns` must include:
  - `workspace_id`, `day`, `compare_to`
  - `day_metrics`, `compare_metrics`, `delta`
- `ai_status.status == "ok"` or `"warning"` (never crashes)

### C) Operator usability (Windows)
- Batch shortcuts for:
  - start server
  - run smoke tests (start/stop server)
  - run UI and bundle fetch
- Auto-port collision handling must be visible.

## Acceptance criteria
- On a clean Windows machine with Python 3.11:
  - `run_smoke_tests_sprint7_7.bat` returns **PASS** and exits 0
  - If port is busy, scripts auto-bump and tests still pass
  - If API key is wrong, tests fail with a clear `[FAIL] auth` reason

## Risks & mitigations
- Port collisions → auto-bump + print chosen port + tests read it
- Different working directories → use `python -m tools...` module execution
- Partial JSON changes → smoke validates minimum keys only, not full payload

