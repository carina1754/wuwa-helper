"""Orchestrate wuthering.gg refreshes into dedicated ``wuwa_*`` tables.

Each ``refresh_*`` discovers the KO data chunk, parses + normalizes it, caches
the entity's icon locally, and upserts by the game's numeric ``Id`` into a
dedicated table (``wuwa_resonator`` / ``wuwa_weapon`` / ``wuwa_echo``). Curated
resonator roles come from the static ``_CURATED_ROLE`` map below (previously
carried over from the now-removed ``character_catalog``). ``fetch`` and ``cache``
are injected so unit tests never touch the network or download real images.
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

# Image categories (the `<category>` path segment under images/), verified live
# against real asset URLs. Only exercised by the real cache during the live load;
# unit tests inject a fake cache.
_CHARACTER_ICON_CATEGORY = "iconrolehead150"
_WEAPON_ICON_CATEGORY = "items"
_ECHO_ICON_CATEGORY = "iconmonstergoods"

# Provenance stamp kept in every record's data_json.
_SOURCE = "wuthering.gg"

# Curated role by game numeric id (only non-default; everything else is main_dps).
# Snapshotted 2026-07 from the now-deprecated character_catalog so wuwa_resonator
# keeps its main_dps / sub_dps / support / healer curation without that table.
_CURATED_ROLE: dict[int, str] = {
    1102: "support",   # 산화
    1103: "healer",    # 설지
    1105: "support",   # 절지
    1106: "healer",    # 유호
    1109: "support",   # 루실라
    1204: "support",   # 모르테피
    1209: "healer",    # 모니에
    1302: "support",   # 음림
    1303: "support",   # 연무
    1307: "healer",    # 복링
    1308: "support",   # 레베카
    1402: "support",   # 양양
    1405: "support",   # 감심
    1408: "healer",    # 방랑자 · 기류
    1410: "support",   # 유노
    1411: "support",   # 구원
    1503: "healer",    # 벨리나
    1505: "healer",    # 파수인
    1506: "support",   # 페비
    1508: "healer",    # 치사
    1601: "support",   # 도기
}


def refresh_characters(*, fetch=client.find_data_chunk, cache=images.cache_asset) -> int:
    text = fetch("characters")
    raw = extract.parse_characters(text)
    count = 0
    with get_connection() as conn:
        for item in raw:
            rec = normalize_character(item)
            rec["image"] = cache(
                "characters", _CHARACTER_ICON_CATEGORY, rec.pop("head_icon_asset")
            )
            # Curated role by game numeric id; default main_dps.
            role = _CURATED_ROLE.get(rec["id"], "main_dps")
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
        # The echo array also carries character/boss "phantom" entries (e.g. 금희,
        # 카를로타) that are not collectable echoes. They are exactly the phantoms
        # whose name is a resonator name, so drop those. (Resonators are refreshed
        # before echoes, so this set is populated.)
        reso_names = {
            r["name_ko"] for r in conn.execute("SELECT name_ko FROM wuwa_resonator").fetchall()
        }
        kept_ids: list[str] = []
        for item in raw:
            rec = normalize_echo(item)
            if rec["name_ko"] in reso_names:
                continue
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
            kept_ids.append(rec["id"])
            count += 1
        # Reconcile: drop rows no longer in the collected set (stale echoes and the
        # previously-inserted character/boss phantoms that the filter now excludes).
        if kept_ids:
            conn.execute("DELETE FROM wuwa_echo WHERE NOT (id = ANY(%s))", (kept_ids,))
        conn.commit()
    return count
