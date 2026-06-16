from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any


def compute_bundle_id(
    workspace_id: str,
    day: str,
    compare_to: str,
    engine_version: str,
    schema_version: str,
) -> str:
    raw = f"{workspace_id}|{day}|{compare_to}|{engine_version}|{schema_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def make_manifest_text(bundle: Mapping[str, Any]) -> str:
    meta = _mapping(bundle.get("meta"))
    ai_status = _mapping(bundle.get("ai_status"))
    ctx = _mapping(meta.get("env_context"))

    lines = [
        "INVYRA_AI_REVIEW_MANIFEST v1",
        f"bundle_id: {meta.get('bundle_id', '')}",
        f"engine_version: {meta.get('engine_version', '')}",
        f"schema_version: {meta.get('schema_version', '')}",
        f"workspace_id: {meta.get('workspace_id', '')}",
        f"day: {meta.get('day', '')}",
        f"compare_to: {meta.get('compare_to', '')}",
        f"generated_at: {meta.get('generated_at', meta.get('generated_at_utc', ''))}",
        f"decision_mode: {meta.get('decision_mode', '')}",
        f"audit_safe: {ai_status.get('audit_safe', True)}",
    ]

    if ctx:
        lines.append("")
        lines.append("[ENV_CONTEXT]")
        for key in (
            "invyra_env",
            "role",
            "terminal",
            "user_id",
            "timezone_offset",
            "locale",
            "os",
            "python",
            "arch",
            "hostname_hash",
            "generated_at_utc",
        ):
            lines.append(f"{key}={ctx.get(key, 'unknown')}")

    return "\n".join(lines) + "\n"
