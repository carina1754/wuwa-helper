"""Regenerate the file-primary datamine catalog artifacts under data/catalog/.

The sim/codex catalog (resonators, weapons, echoes, sonata sets) is served at
runtime from versioned JSON files (see src/catalog.py:_load_catalog_file), NOT
from Postgres. This script (re)generates those files from the current wuwa_* /
sonata_set tables, preserving the exact ORDER BY the old load_* queries used so
the file is a byte-faithful, zero-regression snapshot.

Run after a datamine swap / ingest that updated the tables, then restart the
backend (the files are memoized, same restart-to-deploy model as the sim engine):

    uv run python scripts/export_catalog_to_files.py

Runs against whatever DATABASE_URL points at.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "catalog"

# (artifact name) -> (table, ORDER BY) — must match src/catalog.py load_* ordering.
SPECS = {
    "resonators": ("wuwa_resonator", "ORDER BY rarity DESC NULLS LAST, name_ko"),
    "weapons": ("wuwa_weapon", "ORDER BY rarity DESC NULLS LAST, name_ko"),
    "echoes": ("wuwa_echo", "ORDER BY cost DESC NULLS LAST, rarity DESC NULLS LAST, name_ko"),
    "sonata_sets": ("sonata_set", "ORDER BY name_ko"),
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with get_connection() as conn:
        for name, (table, order) in SPECS.items():
            rows = conn.execute(f"SELECT data_json FROM {table} {order}").fetchall()
            items = [json.loads(r["data_json"]) for r in rows]
            (OUT_DIR / f"{name}.json").write_text(
                json.dumps(items, ensure_ascii=False), encoding="utf-8"
            )
            counts[name] = len(items)

    meta = {
        "sim_source": "datamine-3.5.0",
        "counts": counts,
        "note": "Runtime source of truth. Regenerate with scripts/export_catalog_to_files.py, then restart the backend.",
    }
    (OUT_DIR / "_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {counts} -> {OUT_DIR}")


if __name__ == "__main__":
    main()
