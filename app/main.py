from __future__ import annotations

# Allow running as a script: `python app\main.py`
# (Windows batch files often invoke it this way.)
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.server import run  # noqa: E402


if __name__ == "__main__":
    run()
