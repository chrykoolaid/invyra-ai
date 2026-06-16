# Invyra AI Engine — Sprint A8 GitHub Source Build

This package is intended for direct GitHub upload/commit.

## Notes
- Windows `.bat` runner files have been removed intentionally.
- Source code, app modules, docs, requirements, and tools are retained.
- Sprint A8 adds the environmental/runtime context envelope:
  - `app/env_context.py`
  - `meta.env_context` in review bundle
  - `[ENV_CONTEXT]` in review manifest
  - read-only Env Context UI panel

## Runtime posture
- Review-only
- Kill switch default remains enabled
- No external context APIs
- No engine decision logic changes
