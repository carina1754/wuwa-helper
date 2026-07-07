"""Refresh the wuwa_* tables from the encore.moe API.

Usage:
    uv run python scripts/run_encore_refresh.py [resonators|weapons|echoes|all]
                                                [--no-cache]

Runs against whatever DATABASE_URL points at (use the _dev DB locally). Details
are cached under backend/.encore_cache; pass --no-cache to force live fetches.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.encore import refresh  # noqa: E402


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    use_cache = "--no-cache" not in sys.argv
    target = args[0] if args else "all"
    fns = {
        "resonators": refresh.refresh_resonators,
        "weapons": refresh.refresh_weapons,
        "echoes": refresh.refresh_echoes,
    }
    if target == "all":
        print(refresh.refresh_all(use_cache=use_cache))
    elif target in fns:
        print(target, fns[target](use_cache=use_cache))
    else:
        print(f"unknown target {target!r}; use resonators|weapons|echoes|all")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
