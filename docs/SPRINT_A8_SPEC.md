# Sprint A8 — Environmental (Runtime) Context Envelope (Minimal v1)

## Goal
Attach a deterministic, privacy-safe runtime context envelope to each review bundle.
This improves auditability and future CRM/Nexus compatibility without changing engine behavior.

## Adds
- meta.env_context (always present)
- Manifest includes [ENV_CONTEXT] section
- UI shows Env Context panel

## Safety
- Read-only
- No PII (hostname is hashed)
- No external APIs
