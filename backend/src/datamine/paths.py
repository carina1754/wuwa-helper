from __future__ import annotations

import os
from pathlib import Path

# paths.py → datamine → src → backend → <repo root>
DEFAULT_DATAMINE_ROOT = Path(__file__).resolve().parents[3] / "WutheringWaves_Data-3.5"


def datamine_root() -> Path:
    env = os.getenv("DATAMINE_ROOT")
    return Path(env) if env else DEFAULT_DATAMINE_ROOT
