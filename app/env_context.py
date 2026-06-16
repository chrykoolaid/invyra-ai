from __future__ import annotations

from typing import Any, Dict
import os
import sys
import platform
import hashlib
import locale as pylocale
import time
from datetime import datetime, timezone


def _hash_host(host: str) -> str:
    # Privacy-safe device fingerprint (non-reversible, short)
    salt = "invyra"
    return hashlib.sha256((salt + (host or "unknown")).encode("utf-8")).hexdigest()[:16]


def _tz_offset_hhmm() -> str:
    try:
        offset_sec = -time.timezone
        if time.localtime().tm_isdst and time.daylight:
            offset_sec = -time.altzone
        sign = "+" if offset_sec >= 0 else "-"
        offset_sec = abs(offset_sec)
        hh = offset_sec // 3600
        mm = (offset_sec % 3600) // 60
        return f"{sign}{hh:02d}{mm:02d}"
    except Exception:
        return "unknown"


def get_env_context() -> Dict[str, Any]:
    invyra_env = os.getenv("INVYRA_ENV", "DEV").upper()
    role = os.getenv("INVYRA_ROLE", "UNKNOWN")
    terminal = os.getenv("INVYRA_TERMINAL", "UNKNOWN")
    user_id = os.getenv("INVYRA_USER_ID", "UNKNOWN")

    host = platform.node() or "unknown"
    try:
        loc = (pylocale.getdefaultlocale()[0] or "unknown")
    except Exception:
        loc = "unknown"

    return {
        "invyra_env": invyra_env,
        "role": role,
        "terminal": terminal,
        "user_id": user_id,
        "os": f"{platform.system()} {platform.release()}",
        "python": sys.version.split()[0],
        "arch": platform.machine() or "unknown",
        "locale": loc,
        "timezone_offset": _tz_offset_hhmm(),
        "hostname_hash": _hash_host(host),
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
