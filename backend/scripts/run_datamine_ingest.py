"""Ingest the local datamine (WutheringWaves_Data-3.5) into Postgres.

Usage:
    uv run python scripts/run_datamine_ingest.py

Runs against whatever DATABASE_URL points at (use the _dev DB locally). Reads
the datamine root from DATAMINE_ROOT env or the repo's WutheringWaves_Data-3.5/.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.datamine.ingest import run_ingest  # noqa: E402


def main() -> None:
    print(run_ingest())


if __name__ == "__main__":
    main()
