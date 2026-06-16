"""CI smoke test runner for Invyra AI Review Engine.

Sprint 7.7 hardening:
- Self-contained: starts the server, discovers the port, runs smoke tests, then shuts down.
- Port discovery: reads .invyra_port written by app.server; falls back to probing 8080..8090.
- Works on Windows/Linux/macOS.

Run:
    python -m tools.ci_smoke

Environment:
    INVYRA_AI_INGEST_API_KEY   API key expected by server (default: test_key_123)
    INVYRA_PORT                preferred port (default: 8080)
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Ensure repo root on sys.path when executed from tools/
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.test_runner import run_smoke_tests, wait_for_health  # noqa: E402


PORT_FILE = REPO_ROOT / ".invyra_port"


def _load_port_from_file() -> int | None:
    try:
        p = PORT_FILE.read_text(encoding="utf-8").strip()
        if p.isdigit():
            return int(p)
    except Exception:
        return None
    return None


def _probe_for_port(host: str = "127.0.0.1", start: int = 8080, end: int = 8090) -> int | None:
    """Try a short port range and return the first port that responds to /health."""
    for port in range(start, end + 1):
        ok, _err = wait_for_health(host, port, timeout_s=2.0)
        if ok:
            return port
    return None


def _start_server() -> subprocess.Popen:
    env = os.environ.copy()
    env.setdefault("INVYRA_AI_INGEST_API_KEY", "test_key_123")
    env.setdefault("INVYRA_PORT", env.get("INVYRA_PORT", "8080"))

    # Clear stale port file (if exists)
    try:
        PORT_FILE.unlink(missing_ok=True)  # py>=3.8 supports missing_ok
    except Exception:
        pass

    # Start the engine via our server entry (handles auto-bump)
    cmd = [sys.executable, "-c", "from app.server import run; run()"]

    # On Windows, create a new process group so we can send CTRL_BREAK_EVENT.
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    return subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=creationflags,
    )


def _stop_server(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return

    try:
        if os.name == "nt":
            # Graceful-ish: send CTRL_BREAK so uvicorn can shutdown
            proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
        else:
            proc.send_signal(signal.SIGINT)
        proc.wait(timeout=10)
        return
    except Exception:
        pass

    try:
        proc.terminate()
        proc.wait(timeout=10)
        return
    except Exception:
        pass

    try:
        proc.kill()
    except Exception:
        pass


def _drain_output(proc: subprocess.Popen, max_lines: int = 200) -> str:
    """Best-effort capture of server output (useful when CI fails)."""
    lines: list[str] = []
    if proc.stdout is None:
        return ""

    # Non-blocking-ish: read a bit
    start = time.time()
    while len(lines) < max_lines and time.time() - start < 2.0:
        line = proc.stdout.readline()
        if not line:
            break
        lines.append(line.rstrip("\n"))
    return "\n".join(lines)


def main() -> int:
    host = "127.0.0.1"

    proc = _start_server()
    try:
        # Wait a moment for uvicorn to boot and app.server to write .invyra_port
        deadline = time.time() + 25.0
        port: int | None = None

        while time.time() < deadline:
            if proc.poll() is not None:
                out = _drain_output(proc)
                print("[FAIL] Server exited early.")
                if out:
                    print("--- server output (tail) ---")
                    print(out)
                return 1

            port = _load_port_from_file()
            if port is not None:
                break
            time.sleep(0.2)

        # If still none, probe a small port range
        if port is None:
            port = _probe_for_port(host, 8080, 8090)

        if port is None:
            out = _drain_output(proc)
            print("[FAIL] Could not determine server port (.invyra_port missing and no /health found).")
            if out:
                print("--- server output (tail) ---")
                print(out)
            return 1

        ok, err = wait_for_health(host, port, timeout_s=25.0)
        if not ok:
            out = _drain_output(proc)
            print(f"[FAIL] Server not healthy on {host}:{port}. Last error: {err}")
            if out:
                print("--- server output (tail) ---")
                print(out)
            return 1

        print(f"[OK] Server healthy on http://{host}:{port}")

        api_key = os.environ.get("INVYRA_AI_INGEST_API_KEY", "test_key_123")
        workspace = os.environ.get("INVYRA_WORKSPACE_ID", "ws_test_001")
        day = os.environ.get("INVYRA_DAY", "2026-01-30")
        compare_to = os.environ.get("INVYRA_COMPARE_TO", "2026-01-29")

        # Contract: tools.test_runner.run_smoke_tests() accepts host/port (not base_url).
        results = run_smoke_tests(
            host=host,
            port=port,
            api_key=api_key,
            workspace_id=workspace,
            day=day,
            compare_to=compare_to,
        )

        failed = [r for r in results if not r.ok]
        if failed:
            print("\n[FAIL] Smoke tests failed:")
            for r in failed:
                print(f"  - {r.name}: {r.detail}")
            return 1

        print("\n[PASS] Smoke tests passed.")
        return 0

    finally:
        _stop_server(proc)


if __name__ == "__main__":
    raise SystemExit(main())
