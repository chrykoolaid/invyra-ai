from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json, threading

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
_lock = threading.Lock()

def _path(ws: str) -> Path:
    safe = "".join(c for c in ws if c.isalnum() or c in ("_", "-", ".")).strip()[:80] or "default"
    return DATA_DIR / f"{safe}.json"

def load(ws: str) -> Dict[str, Any]:
    p = _path(ws)
    if not p.exists():
        return {"events": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"events": []}

def save(ws: str, data: Dict[str, Any]) -> None:
    _path(ws).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

def list_events(ws: str) -> List[Dict[str, Any]]:
    with _lock:
        return load(ws).get("events", [])

def append_events(ws: str, events: List[Dict[str, Any]]) -> None:
    with _lock:
        data = load(ws)
        data.setdefault("events", [])
        data["events"].extend(events)
        save(ws, data)
