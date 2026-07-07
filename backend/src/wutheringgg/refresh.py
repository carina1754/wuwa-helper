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
from src.wutheringgg.normalize import (
    normalize_character,
    normalize_echo,
    normalize_weapon,
)

# Image categories (the `<category>` path segment under images/). Only exercised
# by the real cache during the live load; unit tests inject a fake cache.
_CHARACTER_ICON_CATEGORY = "iconrolehead150"
_WEAPON_ICON_CATEGORY = "iconweapon"
_ECHO_ICON_CATEGORY = "iconmonstergoods160"


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
            rec["image"] = cache(
                "characters", _CHARACTER_ICON_CATEGORY, rec.pop("head_icon_asset")
            )
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


def refresh_weapons(*, fetch=client.find_data_chunk, cache=images.cache_asset) -> int:
    text = fetch("weapons")
    raw = extract.parse_weapons(text)
    count = 0
    with get_connection() as conn:
        existing = _existing_sources(conn, "weapon_catalog")
        for item in raw:
            rec = normalize_weapon(item)
            rec["icon"] = cache("weapons", _WEAPON_ICON_CATEGORY, rec.pop("icon_asset"))
            # Preserve a pre-existing row's source (e.g. an earlier namu.wiki import).
            rec["source"] = existing.get(rec["id"], "wuthering.gg")
            conn.execute(
                """
                INSERT INTO weapon_catalog
                    (id, name_ko, weapon_type, rarity, data_json, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name_ko=EXCLUDED.name_ko,
                    weapon_type=EXCLUDED.weapon_type,
                    rarity=EXCLUDED.rarity,
                    data_json=EXCLUDED.data_json,
                    updated_at=now()
                """,
                (
                    rec["id"],
                    rec["name_ko"],
                    rec.get("weapon_type"),
                    rec.get("rarity"),
                    json.dumps(rec, ensure_ascii=False),
                ),
            )
            count += 1
        conn.commit()
    return count


def refresh_echoes(*, fetch=client.find_data_chunk, cache=images.cache_asset) -> int:
    text = fetch("echoes")
    raw = extract.parse_echoes(text)
    count = 0
    with get_connection() as conn:
        existing = _existing_sources(conn, "echo_catalog")
        for item in raw:
            rec = normalize_echo(item)
            rec["icon"] = cache("echoes", _ECHO_ICON_CATEGORY, rec.pop("icon_asset"))
            rec["source"] = existing.get(rec["id"], "wuthering.gg")
            conn.execute(
                """
                INSERT INTO echo_catalog
                    (id, name_ko, cost, data_json, updated_at)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name_ko=EXCLUDED.name_ko,
                    cost=EXCLUDED.cost,
                    data_json=EXCLUDED.data_json,
                    updated_at=now()
                """,
                (
                    rec["id"],
                    rec["name_ko"],
                    rec.get("cost"),
                    json.dumps(rec, ensure_ascii=False),
                ),
            )
            count += 1
        conn.commit()
    return count


def _existing_sources(conn, table: str) -> dict[str, str]:
    """Map id -> existing data_json 'source' for identity preservation on upsert."""
    out: dict[str, str] = {}
    for r in conn.execute(f"SELECT id, data_json FROM {table}").fetchall():  # noqa: S608 - fixed table name
        try:
            src = json.loads(r["data_json"]).get("source")
        except (TypeError, ValueError):
            src = None
        if src:
            out[r["id"]] = src
    return out
