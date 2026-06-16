# Invyra AI Engine — Sprint 7.9A Test Harness & Syntax Fix (No Engine Changes)

Sprint 7.9A is a **pack correctness** update:
- Fixes a **Python syntax error** in `app/web.py` that prevented the server from starting.
- Restores the missing **Sprint 7.9 smoke test runner** batch file.
- Keeps the engine behavior unchanged (review-only, deterministic).

## Manual run (UI)
1) Double-click `start.bat` (or `start_sprint7_9.bat`)
2) Open the printed URL (it will auto-bump the port if 8080 is busy)
3) In the UI, use API key `test_key_123` (default) and click **Load review bundle (recommended)**

## One-command smoke run (recommended)
- Double-click `run_smoke_tests_sprint7_9.bat`
  - Starts server (subprocess)
  - Discovers the port
  - Runs smoke tests
  - Stops the server

## CI
- GitHub Actions: `.github/workflows/ci.yml`
  - Runs `python -m tools.ci_smoke` on Windows + Ubuntu.
