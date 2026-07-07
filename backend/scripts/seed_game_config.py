"""Seed game-math constants into the local DB (game_config table).

These are Wuthering Waves game constants the encore API does not expose (echo
main-stat max values by cost, sub-stat roll ranges, sub-stat slots by grade,
echo cost budget). Storing them in the DB keeps all game data server-side; the
party builder fetches them via /game-config instead of hardcoding.

Usage: uv run python scripts/seed_game_config.py   (targets DATABASE_URL)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection  # noqa: E402

ECHO_STATS = {
    "costBudget": 12,
    # echo main-stat options + level-25 (5★) max value, by cost
    "main": {
        "1": [
            {"key": "hp", "max": 2280}, {"key": "atkPct", "max": 18.0},
            {"key": "hpPct", "max": 22.8}, {"key": "defPct", "max": 18.0},
        ],
        "3": [
            {"key": "atkPct", "max": 30.0}, {"key": "hpPct", "max": 30.0}, {"key": "defPct", "max": 38.0},
            {"key": "energyRegen", "max": 32.0},
            {"key": "glacioDmg", "max": 30.0}, {"key": "fusionDmg", "max": 30.0}, {"key": "electroDmg", "max": 30.0},
            {"key": "aeroDmg", "max": 30.0}, {"key": "spectroDmg", "max": 30.0}, {"key": "havocDmg", "max": 30.0},
        ],
        "4": [
            {"key": "crit", "max": 22.0}, {"key": "critDmg", "max": 44.0},
            {"key": "atkPct", "max": 33.0}, {"key": "hpPct", "max": 33.0}, {"key": "defPct", "max": 41.8},
            {"key": "atk", "max": 150}, {"key": "healing", "max": 26.4},
        ],
    },
    # sub-stat pool + per-roll range
    "sub": [
        {"key": "hp", "min": 320, "max": 580},
        {"key": "atk", "min": 30, "max": 70},
        {"key": "def", "min": 30, "max": 70},
        {"key": "hpPct", "min": 6.4, "max": 11.6},
        {"key": "atkPct", "min": 6.4, "max": 11.6},
        {"key": "defPct", "min": 8.1, "max": 14.7},
        {"key": "crit", "min": 6.3, "max": 10.5},
        {"key": "critDmg", "min": 12.6, "max": 21.0},
        {"key": "energyRegen", "min": 5.6, "max": 14.9},
        {"key": "skillDmg", "min": 6.4, "max": 12.4},
        {"key": "basicDmg", "min": 6.4, "max": 11.6},
        {"key": "heavyDmg", "min": 6.4, "max": 11.6},
        {"key": "liberationDmg", "min": 6.4, "max": 11.6},
    ],
    # sub-stat slots available at each echo grade (star)
    "subSlots": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
}

CONFIGS = {"echo_stats": ECHO_STATS}


def main() -> None:
    with get_connection() as conn:
        for cid, data in CONFIGS.items():
            conn.execute(
                """
                INSERT INTO game_config (id, data_json, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (id) DO UPDATE SET data_json = EXCLUDED.data_json, updated_at = now()
                """,
                (cid, json.dumps(data, ensure_ascii=False)),
            )
        conn.commit()
    print("seeded game_config:", ", ".join(CONFIGS))


if __name__ == "__main__":
    main()
