from __future__ import annotations
from pathlib import Path
from typing import Optional
import json, os, time, urllib.request

LOCK_PATH = Path(__file__).resolve().parent.parent / ".invyra_ai_lock.json"

def _ping(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=0.8) as r:
            return r.status == 200
    except Exception:
        return False

def check_existing() -> Optional[int]:
    if not LOCK_PATH.exists():
        return None
    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        port = int(data.get("port"))
    except Exception:
        return None
    if _ping(port):
        return port
    try:
        LOCK_PATH.unlink()
    except Exception:
        pass
    return None

def write_lock(port: int) -> None:
    try:
        LOCK_PATH.write_text(json.dumps({
            "port": port,
            "pid": os.getpid(),
            "started_at": int(time.time())
        }, indent=2), encoding="utf-8")
    except Exception:
        pass

def clear_lock() -> None:
    try:
        if LOCK_PATH.exists():
            LOCK_PATH.unlink()
    except Exception:
        pass
