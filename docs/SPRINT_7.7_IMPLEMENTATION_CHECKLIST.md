# Sprint 7.7 Implementation Checklist (CI + Test Harness)

## 1) Versioning
- [ ] Bump `engine_version` / `APP_VERSION` to `sprint-7.7-test-pack-01`
- [ ] Confirm `schema_version` remains unchanged unless intentionally bumped

## 2) Smoke-test contract (tools)
- [ ] `tools/ci_smoke.py` runs via `python -m tools.ci_smoke`
- [ ] Arguments: host/port/workspace/day/compare/api_key
- [ ] Exit codes: pass=0, fail=2, infra=3
- [ ] Error messages include single root-cause (auth / server-not-ready / contract-missing)

## 3) Bundle contract validation
- [ ] CI checks `/review/bundle` 200 OK
- [ ] Validates required keys: meta/ai_status/deterministic_patterns/ai_explanation
- [ ] Validates meta keys: schema_version/engine_version
- [ ] Validates deterministic patterns keys: workspace_id/day/compare_to/day_metrics/compare_metrics/delta

## 4) Windows runner scripts
- [ ] `start_sprint7_7.bat` launches server with auto-bump message
- [ ] `run_smoke_tests_sprint7_7.bat` starts server, waits health, runs bundle validation, exits with code
- [ ] `run_all_sprint7_7.bat` convenience script (deps + server + open browser)

## 5) Regression checks
- [ ] UI still loads at `/ui/ai-review`
- [ ] “Load review bundle” works
- [ ] Legacy calls remain behind “Advanced” toggle (if present)

## 6) QA sign-off (quick)
- [ ] Smoke tests PASS on a machine where port 8080 is free
- [ ] Smoke tests PASS when port 8080 is busy (auto-bumped)
- [ ] Incorrect API key produces clear FAIL (401)
- [ ] No engine behavior changes: review-only locked
