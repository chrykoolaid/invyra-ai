# Sprint 7.8 — Review Output Maturity (UI Export + Build Metadata)

## Goal
Improve **human review output usability** without changing engine behavior:
- Export loaded `/review/bundle` as JSON from the UI
- Surface build metadata clearly in UI

## Non-goals
- No action execution
- No AI enablement changes
- No API schema changes

## Changes
1) UI adds:
- **Download Bundle JSON**
- **Copy Bundle JSON**
(Enabled only after a bundle is successfully loaded.)

2) UI shows:
- Build: `sprint-7.8-test-pack-01`

## Acceptance
- Smoke tests pass
- UI bundle load still works
- Export buttons produce valid JSON matching the loaded bundle
