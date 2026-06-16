# Sprint 7.5 — Test Harness & CI Hardening (Option A)

## Quick start

### 1) Start the server (manual)

Double‑click:
- `start_sprint7_5.bat`

It will:
- set a default dev API key: `test_key_123` (unless you already set one)
- start the server (defaults to port 8080; auto-bumps if busy)
- print the URL to open

### 2) Run smoke tests (manual)

With the server running, double‑click:
- `test_sprint7_5.bat`

### 3) One command (recommended)

Double‑click:
- `run_smoke_tests_sprint7_5.bat`

This starts the server, runs smoke tests, and shuts the server down.

## What the smoke tests validate

- `GET /health` returns **200**
- `GET /ui/ai-review` returns **200**
- Missing API key for a protected endpoint returns **401**
- `GET /review/bundle` with API key returns **200** and includes:
  - `ai_status`
  - `deterministic_patterns`
  - `ai_explanation`
  - `schema_version`
  - `engine_version`

## CI

A GitHub Actions workflow is included at:
- `.github/workflows/ci.yml`

It installs dependencies and runs `python tools/ci_smoke.py`.

## Stage A8 (Environmental Context)

- Start server: `start_A8.bat`
- Run smoke tests: `test_A8.bat` (or `run_smoke_tests_A8.bat`)
