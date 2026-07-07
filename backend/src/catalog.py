"""Weapon (and later echo/character) catalog: crawl Namuwiki → cache icons → DB."""
from __future__ import annotations

import hashlib
import json

from .database import get_connection
from .media import ensure_catalog_image
from .models import WeaponCatalogItem
from .namu.client import fetch_page, sub_page
from .namu.weapons import parse_weapons


def weapon_id(name_ko: str) -> str:
    """Stable, URL/filesystem-safe id derived from the Korean weapon name."""
    return "w-" + hashlib.sha1(name_ko.encode("utf-8")).hexdigest()[:12]


def refresh_weapon_catalog() -> int:
    """Crawl the Namuwiki weapon list, cache each icon locally, upsert to DB.

    Any weapon-type page embeds the full master weapon table, so one fetch is
    enough. Returns the number of weapons upserted.
    """
    weapons = parse_weapons(fetch_page(sub_page("무기", "권총")))
    if not weapons:
        return 0
    with get_connection() as conn:
        for weapon in weapons:
            wid = weapon_id(weapon["name_ko"])
            icon = ensure_catalog_image("weapons", wid, weapon.get("icon_source"))
            item = {
                "id": wid,
                "name_ko": weapon["name_ko"],
                "weapon_type": weapon.get("weapon_type"),
                "rarity": weapon.get("rarity"),
                "icon": icon,
                "source": "namu.wiki",
            }
            conn.execute(
                """
                INSERT INTO weapon_catalog (id, name_ko, weapon_type, rarity, data_json, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name_ko = EXCLUDED.name_ko,
                    weapon_type = EXCLUDED.weapon_type,
                    rarity = EXCLUDED.rarity,
                    data_json = EXCLUDED.data_json,
                    updated_at = now()
                """,
                (wid, item["name_ko"], item["weapon_type"], item["rarity"],
                 json.dumps(item, ensure_ascii=False)),
            )
        conn.commit()
    return len(weapons)


def load_weapon_catalog() -> list[WeaponCatalogItem]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT data_json FROM weapon_catalog ORDER BY rarity DESC NULLS LAST, name_ko"
        ).fetchall()
    return [WeaponCatalogItem.model_validate_json(row["data_json"]) for row in rows]
