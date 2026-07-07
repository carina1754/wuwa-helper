"""Orchestrate wuthering.gg refreshes into dedicated ``wuwa_*`` tables.

Each ``refresh_*`` discovers the KO data chunk, parses + normalizes it, caches
the entity's icon locally, and upserts by the game's numeric ``Id`` into a
dedicated table (``wuwa_resonator`` / ``wuwa_weapon`` / ``wuwa_echo``). These
tables are owned exclusively by the wuthering.gg pipeline, so the existing
curated catalog tables (``character_catalog`` / ``weapon_catalog`` /
``echo_catalog``) are never mutated here. ``fetch`` and ``cache`` are injected so
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

# Provenance stamp kept in every record's data_json.
_SOURCE = "wuthering.gg"


def refresh_characters(*, fetch=client.find_data_chunk, cache=images.cache_asset) -> int:
    text = fetch("characters")
    raw = extract.parse_characters(text)
    count = 0
    with get_connection() as conn:
        # Carry over the curated role from character_catalog by matching the
        # game numeric id (character_catalog.id and wuwa_resonator.id are both
        # the game Id). Default to "main_dps" when there is no catalog row.
        catalog_roles = {
            r["id"]: r["role"]
            for r in conn.execute("SELECT id, role FROM character_catalog").fetchall()
        }
        for item in raw:
            rec = normalize_character(item)
            rec["image"] = cache(
                "characters", _CHARACTER_ICON_CATEGORY, rec.pop("head_icon_asset")
            )
            role = catalog_roles.get(rec["id"], "main_dps")
            rec["role"] = role
            rec["source"] = _SOURCE
            conn.execute(
                """
                INSERT INTO wuwa_resonator
                    (id, name_ko, name_en, element, weapon_type, rarity, role, data_json, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name_ko=EXCLUDED.name_ko,
                    name_en=EXCLUDED.name_en,
                    element=EXCLUDED.element,
                    weapon_type=EXCLUDED.weapon_type,
                    rarity=EXCLUDED.rarity,
                    role=EXCLUDED.role,
                    data_json=EXCLUDED.data_json,
                    updated_at=now()
                """,
                (
                    rec["id"],
                    rec.get("name"),
                    rec.get("name_en"),
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
        for item in raw:
            rec = normalize_weapon(item)
            rec["icon"] = cache("weapons", _WEAPON_ICON_CATEGORY, rec.pop("icon_asset"))
            rec["source"] = _SOURCE
            conn.execute(
                """
                INSERT INTO wuwa_weapon
                    (id, name_ko, name_en, weapon_type, rarity, data_json, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name_ko=EXCLUDED.name_ko,
                    name_en=EXCLUDED.name_en,
                    weapon_type=EXCLUDED.weapon_type,
                    rarity=EXCLUDED.rarity,
                    data_json=EXCLUDED.data_json,
                    updated_at=now()
                """,
                (
                    rec["id"],
                    rec.get("name_ko"),
                    rec.get("name_en"),
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
        for item in raw:
            rec = normalize_echo(item)
            rec["icon"] = cache("echoes", _ECHO_ICON_CATEGORY, rec.pop("icon_asset"))
            rec["source"] = _SOURCE
            conn.execute(
                """
                INSERT INTO wuwa_echo
                    (id, name_ko, name_en, cost, rarity, data_json, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name_ko=EXCLUDED.name_ko,
                    name_en=EXCLUDED.name_en,
                    cost=EXCLUDED.cost,
                    rarity=EXCLUDED.rarity,
                    data_json=EXCLUDED.data_json,
                    updated_at=now()
                """,
                (
                    rec["id"],
                    rec.get("name_ko"),
                    rec.get("name_en"),
                    rec.get("cost"),
                    rec.get("rarity"),
                    json.dumps(rec, ensure_ascii=False),
                ),
            )
            count += 1
        conn.commit()
    return count
