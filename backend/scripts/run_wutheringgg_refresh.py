"""Refresh wuthering.gg data into the wuwa_* dev tables.

Discovery (finding the KO data chunk) is the expensive step, so it is cached to
disk under ``.wuwagg_chunks/`` and the per-entity loads reuse it — this lets the
three entity loads run in parallel without each re-downloading hundreds of chunks.

Usage:
  python scripts/run_wutheringgg_refresh.py discover     # find + cache the 3 KO data chunks
  python scripts/run_wutheringgg_refresh.py characters   # load resonators from the cached chunk
  python scripts/run_wutheringgg_refresh.py weapons
  python scripts/run_wutheringgg_refresh.py echoes
  python scripts/run_wutheringgg_refresh.py all          # discover + load all three sequentially
"""
from __future__ import annotations

import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import database_url  # noqa: E402

_root, _ = database_url().rsplit("/", 1)
os.environ["DATABASE_URL"] = _root + "/wuwa_ai_coach_dev"

from src.database import init_db  # noqa: E402
from src.wutheringgg import client, refresh  # noqa: E402

CACHE_DIR = pathlib.Path(
    os.environ.get("WUWAGG_CACHE", pathlib.Path(__file__).resolve().parents[1] / ".wuwagg_chunks")
)
KINDS = ("characters", "weapons", "echoes")
_REFRESH = {
    "characters": refresh.refresh_characters,
    "weapons": refresh.refresh_weapons,
    "echoes": refresh.refresh_echoes,
}


def _chunk_path(kind: str) -> pathlib.Path:
    return CACHE_DIR / f"{kind}.js"


def discover() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for kind in KINDS:
        text = client.find_data_chunk(kind)
        _chunk_path(kind).write_text(text, encoding="utf-8")
        print(f"discovered {kind}: {len(text)} chars -> {_chunk_path(kind)}", flush=True)


def load(kind: str) -> int:
    path = _chunk_path(kind)
    text = path.read_text(encoding="utf-8") if path.exists() else client.find_data_chunk(kind)
    count = _REFRESH[kind](fetch=lambda _k: text)
    print(f"loaded {kind}: {count}", flush=True)
    return count


if __name__ == "__main__":
    init_db()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "discover":
        discover()
    elif cmd in KINDS:
        load(cmd)
    elif cmd == "all":
        discover()
        for k in KINDS:
            load(k)
    else:
        raise SystemExit(f"unknown command: {cmd!r} (use: discover | {' | '.join(KINDS)} | all)")
