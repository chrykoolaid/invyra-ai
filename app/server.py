from __future__ import annotations
import os, socket, atexit
import uvicorn
from .instance_guard import check_existing, write_lock, clear_lock

def _is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
        return True

def choose_port(preferred: int) -> int:
    if _is_free(preferred):
        return preferred
    for p in range(preferred+1, preferred+21):
        if _is_free(p):
            return p
    return preferred

def run():
    from .web import app

    existing = check_existing()
    if existing is not None:
        print(f"[INSTANCE] Existing server detected on port {existing}")
        print("[INSTANCE] Aborting startup")
        return

    preferred = int(os.getenv("INVYRA_PORT", os.getenv("INVYRA_AI_PORT","8080")))
    host = os.getenv("INVYRA_AI_HOST","0.0.0.0")

    port = choose_port(preferred)
    if port != preferred:
        print(f"[PORT] {preferred} in use")
        print(f"[PORT] Selected {port}")

    write_lock(port)
    # Persist chosen port for smoke tests / CI runners
    try:
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        (root / ".invyra_port").write_text(str(port), encoding="utf-8")
    except Exception:
        pass
    atexit.register(clear_lock)

    print(f"[SERVER] Starting on http://localhost:{port}")
    print(f"Open: http://localhost:{port}/ui/ai-review")

    uvicorn.run(app, host=host, port=port, log_level=os.getenv("INVYRA_LOG_LEVEL","info"))
