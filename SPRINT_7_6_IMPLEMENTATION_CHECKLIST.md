# Sprint 7.6 — Implementation Checklist (Dev + QA)

## 1) Server start/stop for CI
- [ ] CI smoke runner starts the server in a subprocess (no manual window spawning).
- [ ] Runner discovers chosen port via `.invyra_port` (and has a probe fallback).
- [ ] Runner waits for `/health` OK before running requests.
- [ ] Runner terminates server on success/failure and cleans up.

## 2) Smoke coverage
- [ ] `/health` returns 200 and JSON.
- [ ] `/ai/status` returns 200 and includes `engine_version` and `schema_version`.
- [ ] `/review/bundle` returns 200 with keys: `ai_status`, `deterministic_patterns`, `ai_explanation`.
- [ ] Negative auth: request without key (or wrong key) returns 401 (or 403).

## 3) Port collision resilience
- [ ] If 8080 is busy, server bumps (8081, 8082...) and writes `.invyra_port`.
- [ ] CI smoke runner still passes after auto-bump.

## 4) GitHub Actions
- [ ] Workflow runs on Windows + Ubuntu.
- [ ] Workflow installs deps and runs `python -m tools.ci_smoke`.
- [ ] Workflow exits non-zero on any smoke failure.

## 5) Local developer ergonomics
- [ ] `run_smoke_tests_sprint7_6.bat` works from a double-click.
- [ ] README_TEST.md includes correct instructions.

## Done definition
- [ ] Green CI on both OS targets.
- [ ] Local smoke run passes twice in a row (repeatability).
