"""Orchestrate wuthering.gg refreshes into the catalog tables.

Each ``refresh_*`` discovers the KO data chunk, parses + normalizes it, caches
the entity's icon locally, and upserts by the game's numeric ``Id`` while
preserving any identity a pre-existing row already carries (a character's
``role``, a weapon/echo's ``source``). ``fetch`` and ``cache`` are injected so
unit tests never touch the network or download real images.
"""
from __future__ import annotations

import json

from src.database import get_connection
from src.wutheringgg import client, extract, images
from src.wutheringgg.normalize import normalize_character


def refresh_characters(*, fetch=client.find_data_chunk, cache=images.cache_asset) -> int:
    text = fetch("characters")
    raw = extract.parse_characters(text)
    count = 0
    with get_connection() as conn:
        existing = {
            r["id"]: r["role"]
            for r in conn.execute("SELECT id, role FROM character_catalog").fetchall()
        }
        for item in raw:
            rec = normalize_character(item)
            rec["image"] = cache("characters", "iconrolehead150", rec.pop("head_icon_asset"))
            role = existing.get(rec["id"], "main_dps")
            rec["role"] = role
            conn.execute(
                """
                INSERT INTO character_catalog
                    (id, name, element, weapon_type, rarity, role, data_json, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name=EXCLUDED.name,
                    element=EXCLUDED.element,
                    weapon_type=EXCLUDED.weapon_type,
                    rarity=EXCLUDED.rarity,
                    data_json=EXCLUDED.data_json,
                    updated_at=now()
                """,
                (
                    rec["id"],
                    rec["name"],
                    rec.get("element"),
                    rec.get("weapon_type"),
                    rec.get("rarity"),
                    role,
                    json.dumps(rec, ensure_ascii=False),
                ),
            )
            count += 1
        conn.commit()
    return count
