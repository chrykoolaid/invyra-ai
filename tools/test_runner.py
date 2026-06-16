import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

DEFAULT_HOST = os.environ.get("INVYRA_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("INVYRA_PORT", "8080"))
DEFAULT_KEY = os.environ.get("INVYRA_AI_INGEST_API_KEY", "test_key_123")


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""


def _url(host: str, port: int, path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return f"http://{host}:{port}{path}"


def _request_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 5.0) -> Tuple[int, Any]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = getattr(r, "status", 200)
            raw = r.read().decode("utf-8", errors="replace")
            if raw.strip() == "":
                return status, None
            # Try JSON, fall back to text
            try:
                return status, json.loads(raw)
            except Exception:
                return status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        try:
            body = json.loads(raw) if raw else None
        except Exception:
            body = raw
        return e.code, body


def wait_for_health(host: str, port: int, timeout_s: float = 20.0):
    """CI-friendly health wait.

    Returns:
        (ok, last_error)

    Notes:
        - Never raises (callers decide how to handle failure)
        - This keeps `ci_smoke.py` simple and avoids unpacking None.
    """
    deadline = time.time() + timeout_s
    last_err = ""
    while time.time() < deadline:
        try:
            code, body = _request_json(_url(host, port, "/health"))
            if code == 200 and isinstance(body, dict) and body.get("status") == "ok":
                return True, None
            last_err = f"health returned {code}: {body}"
        except Exception as e:
            last_err = str(e)
        time.sleep(0.4)
    return False, last_err or "timeout"


def run_smoke_tests(host: str, port: int, api_key: str, workspace_id: str = "ws_test_001", day: str = "2026-01-30", compare_to: str = "2026-01-29") -> list[Result]:
    results: list[Result] = []

    def ok(name: str, detail: str = ""):
        results.append(Result(name=name, ok=True, detail=detail))

    def bad(name: str, detail: str):
        results.append(Result(name=name, ok=False, detail=detail))

    # 1) Health
    try:
        code, body = _request_json(_url(host, port, "/health"))
        if code == 200 and isinstance(body, dict) and body.get("status") == "ok":
            ok("health")
        else:
            bad("health", f"expected 200 ok json, got {code}: {body}")
    except Exception as e:
        bad("health", str(e))

    # 2) UI HTML reachable
    try:
        code, body = _request_json(_url(host, port, "/ui/ai-review"))
        if code == 200 and isinstance(body, str) and "AI" in body:
            ok("ui/ai-review")
        else:
            bad("ui/ai-review", f"expected 200 html, got {code}")
    except Exception as e:
        bad("ui/ai-review", str(e))

    # 3) Unauthorized without key (patterns)
    try:
        code, body = _request_json(_url(host, port, f"/patterns/day?workspace_id={workspace_id}&day={day}&compare_to={compare_to}"))
        if code == 401:
            ok("patterns unauthorized")
        else:
            bad("patterns unauthorized", f"expected 401, got {code}: {body}")
    except Exception as e:
        bad("patterns unauthorized", str(e))

    headers = {"X-API-Key": api_key}

    # 4) Authorized patterns
    try:
        code, body = _request_json(_url(host, port, f"/patterns/day?workspace_id={workspace_id}&day={day}&compare_to={compare_to}"), headers=headers)
        # Backward/forward compatible schema check:
        # - Legacy: {"metrics": {...}}
        # - Current: {"workspace_id":..., "day_metrics":..., "compare_metrics":..., "delta":...}
        if code == 200 and isinstance(body, dict):
            if "metrics" in body:
                ok("patterns authorized")
            elif all(k in body for k in ("day_metrics", "compare_metrics", "delta")):
                ok("patterns authorized")
            else:
                bad("patterns authorized", f"expected patterns payload, got keys={list(body.keys())}")
        else:
            bad("patterns authorized", f"expected 200 json, got {code}: {body}")
    except Exception as e:
        bad("patterns authorized", str(e))

    # 5) Authorized bundle
    try:
        code, body = _request_json(_url(host, port, f"/review/bundle?workspace_id={workspace_id}&day={day}&compare_to={compare_to}"), headers=headers)
        if code != 200 or not isinstance(body, dict):
            bad("bundle authorized", f"expected 200 json, got {code}: {body}")
        else:
            # Bundle contract (forward compatible):
            # Current server returns: {meta:{schema_version,engine_version}, ai_status,...}
            # Older builds returned schema_version/engine_version at top-level.
            required = ["ai_status", "deterministic_patterns", "ai_explanation", "meta"]
            missing_required = [k for k in required if k not in body]
            if missing_required:
                bad("bundle schema", f"missing keys: {missing_required}. keys={list(body.keys())}")
            else:
                meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
                schema_version = body.get("schema_version") or meta.get("schema_version")
                engine_version = body.get("engine_version") or meta.get("engine_version")
                if not schema_version or not engine_version:
                    bad(
                        "bundle schema",
                        f"missing version fields (schema_version/engine_version). keys={list(body.keys())} meta_keys={list(meta.keys())}",
                    )
                else:
                    ok("bundle authorized")
                    ok("bundle schema")
    except Exception as e:
        bad("bundle authorized", str(e))

    return results


def main(argv: Optional[list[str]] = None) -> int:
    argv = argv or sys.argv[1:]

    host = DEFAULT_HOST
    port = DEFAULT_PORT
    api_key = DEFAULT_KEY

    # Optional CLI: host port key
    if len(argv) >= 1:
        host = argv[0]
    if len(argv) >= 2:
        port = int(argv[1])
    if len(argv) >= 3:
        api_key = argv[2]

    print(f"[TEST] Target: http://{host}:{port}  key=***{api_key[-4:]}  (workspace=ws_test_001)")

    ok, err = wait_for_health(host, port)
    if not ok:
        print(f"[FAIL] Server not healthy on {host}:{port} within 20.0s. Last error: {err}")
        return 2

    results = run_smoke_tests(host, port, api_key)

    failed = [r for r in results if not r.ok]
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        print(f"[{status}] {r.name}" + (f" :: {r.detail}" if (r.detail and not r.ok) else ""))

    if failed:
        print(f"\n[SUMMARY] FAIL ({len(failed)}/{len(results)} failed)")
        return 1

    print(f"\n[SUMMARY] OK ({len(results)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
