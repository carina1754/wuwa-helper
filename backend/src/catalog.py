"""Catalog: crawl Namuwiki → normalize → cache icons → store in PostgreSQL.

Covers weapons, character kits (skills/chains/builds), sonata sets and echoes.
Everything is keyed by a stable hash of the Korean name and stored as a
data_json blob so the schema can evolve without migrations.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json

from .database import get_connection
from .media import ensure_catalog_image
from .models import PickupBanner, WeaponCatalogItem
from .namu import characters as namu_characters
from .namu import echoes as namu_echoes
from .namu.banners import parse_banner_history
from .namu.client import fetch_page, sub_page
from .namu.weapons import parse_weapons


def _hash_id(prefix: str, name_ko: str) -> str:
    return prefix + hashlib.sha1(name_ko.encode("utf-8")).hexdigest()[:12]


def weapon_id(name_ko: str) -> str:
    """Stable, URL/filesystem-safe id derived from the Korean weapon name."""
    return _hash_id("w-", name_ko)


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


# --- Character kits (skills, resonance chains, recommended builds) -----------
# Namuwiki character pages, keyed by Korean name. Rich data for the pickup
# schedule and a future AI recommendation system.
CHARACTER_NAMES = [
    "경연", "구원", "금희", "도기", "레베카", "로코코", "루미", "루시", "루실라",
    "린네", "방랑자", "벨리나", "브렌트", "산화", "샤콘", "수수", "수호신", "스카",
    "아우구스타", "알토", "앙코", "양양", "연무", "유노", "유호", "절지", "치사",
    "카를로타", "카멜리아", "카카루", "칸타렐라", "황룡",
]


def character_page_title(name_ko: str) -> str:
    return f"{name_ko}(명조: 워더링 웨이브)"


def refresh_character_kits(max_workers: int = 6) -> int:
    """Fetch every character page (concurrently), parse, store the kit."""

    def fetch_parse(name_ko: str):
        try:
            kit = namu_characters.parse_character(fetch_page(character_page_title(name_ko)))
        except Exception:
            return None
        return kit if kit and kit.get("name_ko") else None

    kits: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        for kit in pool.map(fetch_parse, CHARACTER_NAMES):
            if kit:
                kits.append(kit)

    with get_connection() as conn:
        for kit in kits:
            cid = _hash_id("c-", kit["name_ko"])
            kit = {**kit, "id": cid}
            conn.execute(
                """
                INSERT INTO character_kit (id, name_ko, data_json, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name_ko = EXCLUDED.name_ko,
                    data_json = EXCLUDED.data_json,
                    updated_at = now()
                """,
                (cid, kit["name_ko"], json.dumps(kit, ensure_ascii=False)),
            )
        conn.commit()
    return len(kits)


def load_character_kits() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT data_json FROM character_kit ORDER BY name_ko").fetchall()
    return [json.loads(row["data_json"]) for row in rows]


# --- Echoes (sonata sets + individual echoes) --------------------------------
_ECHO_TIER_PAGES = ["해일급", "노도급", "거랑급", "경파급"]


def refresh_echo_catalog() -> int:
    """Crawl sonata sets + all echoes, cache icons, store. Returns rows written."""
    sonata_sets = namu_echoes.parse_sonata_sets(fetch_page(sub_page("데이터 스테이션")))
    echoes: list[dict] = []
    seen: set[str] = set()
    for tier in _ECHO_TIER_PAGES:
        try:
            parsed = namu_echoes.parse_echoes(fetch_page(sub_page("적", tier)), sonata_sets)
        except Exception:
            continue
        for echo in parsed:
            if echo.get("name_ko") and echo["name_ko"] not in seen:
                seen.add(echo["name_ko"])
                echoes.append(echo)

    with get_connection() as conn:
        for setinfo in sonata_sets:
            sid = _hash_id("s-", setinfo["name_ko"])
            icon = ensure_catalog_image("echoes", sid, setinfo.get("icon"))
            item = {**setinfo, "id": sid, "icon": icon}
            conn.execute(
                """
                INSERT INTO sonata_set (id, name_ko, data_json, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name_ko = EXCLUDED.name_ko, data_json = EXCLUDED.data_json, updated_at = now()
                """,
                (sid, item["name_ko"], json.dumps(item, ensure_ascii=False)),
            )
        for echo in echoes:
            eid = _hash_id("e-", echo["name_ko"])
            icon = ensure_catalog_image("echoes", eid, echo.get("icon"))
            item = {**echo, "id": eid, "icon": icon}
            conn.execute(
                """
                INSERT INTO echo_catalog (id, name_ko, cost, data_json, updated_at)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name_ko = EXCLUDED.name_ko, cost = EXCLUDED.cost,
                    data_json = EXCLUDED.data_json, updated_at = now()
                """,
                (eid, item["name_ko"], echo.get("cost"), json.dumps(item, ensure_ascii=False)),
            )
        conn.commit()
    return len(sonata_sets) + len(echoes)


def load_sonata_sets() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT data_json FROM sonata_set ORDER BY name_ko").fetchall()
    return [json.loads(row["data_json"]) for row in rows]


def load_echoes() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT data_json FROM echo_catalog ORDER BY cost DESC NULLS LAST, name_ko"
        ).fetchall()
    return [json.loads(row["data_json"]) for row in rows]


# --- Pickup banners (characters + weapons per version/phase) ------------------
# Crawled from Namuwiki 튜닝 pages; character + weapon banners merged by
# (version, phase). Character avatars are pulled from the banner page's own
# icons (alt names the character) and cached; weapons are matched to
# weapon_catalog by Korean name for their icon/rarity/type.
def _char_avatar_source(name_ko: str, icons: list[dict] | None) -> str | None:
    for icon in icons or []:
        alt = icon.get("alt") or ""
        if name_ko in alt and "아이콘" not in alt and "패턴" not in alt and "로고" not in alt:
            return icon.get("src")
    return None


def refresh_pickup_banners() -> int:
    """Crawl character + weapon banner history, merge, cache avatars, store."""
    char_banners = parse_banner_history(fetch_page(sub_page("튜닝", "캐릭터 이벤트 튜닝")), "character")
    weapon_banners = parse_banner_history(fetch_page(sub_page("튜닝", "무기 이벤트 튜닝")), "weapon")
    weapon_by_name = {w.name_ko: w for w in load_weapon_catalog()}

    merged: dict[tuple, dict] = {}

    def slot(banner: dict) -> dict:
        key = (banner["version"], banner.get("phase"))
        return merged.setdefault(
            key,
            {
                "version": banner["version"],
                "phase": banner.get("phase"),
                "banner_name": banner.get("banner_name"),
                "is_rerun": banner.get("is_rerun", False),
                "characters": [],
                "weapons": [],
                "start_date": banner.get("start_date"),
                "end_date": banner.get("end_date"),
            },
        )

    for banner in char_banners:
        entry = slot(banner)
        for name in banner.get("items", []):
            cid = _hash_id("c-", name)
            avatar = ensure_catalog_image(
                "characters", cid, _char_avatar_source(name, banner.get("icons"))
            )
            entry["characters"].append({"name_ko": name, "avatar": avatar})

    for banner in weapon_banners:
        entry = slot(banner)
        for name in banner.get("items", []):
            weapon = weapon_by_name.get(name)
            entry["weapons"].append(
                {
                    "name_ko": name,
                    "icon": weapon.icon if weapon else None,
                    "rarity": weapon.rarity if weapon else None,
                    "weapon_type": weapon.weapon_type if weapon else None,
                }
            )

    with get_connection() as conn:
        conn.execute("DELETE FROM pickup_banners")
        for (version, phase), entry in merged.items():
            bid = f"{version}-p{phase}"
            entry["id"] = bid
            conn.execute(
                """
                INSERT INTO pickup_banners (id, version, phase, data_json, updated_at)
                VALUES (%s, %s, %s, %s, now())
                """,
                (bid, version, phase, json.dumps(entry, ensure_ascii=False)),
            )
        conn.commit()
    return len(merged)


def refresh_character_catalog_images() -> int:
    """Cache the character_catalog avatar/splash images locally and rewrite the
    stored URLs to our served paths (idempotent — skips already-local paths)."""
    with get_connection() as conn:
        rows = conn.execute("SELECT id, data_json FROM character_catalog").fetchall()
        updated = 0
        for row in rows:
            data = json.loads(row["data_json"])
            base = f"cat-{data.get('id')}"
            changed = False
            for field, item_id in (("image", base), ("splash_image", f"{base}-splash")):
                src = data.get(field)
                if isinstance(src, str) and src.startswith("http"):
                    local = ensure_catalog_image("characters", item_id, src)
                    if local:
                        data[field] = local
                        changed = True
            if changed:
                conn.execute(
                    "UPDATE character_catalog SET data_json = %s, updated_at = now() WHERE id = %s",
                    (json.dumps(data, ensure_ascii=False), row["id"]),
                )
                updated += 1
        conn.commit()
    return updated


def load_pickup_banners() -> list[PickupBanner]:
    with get_connection() as conn:
        rows = conn.execute("SELECT data_json FROM pickup_banners").fetchall()
    banners = [PickupBanner.model_validate_json(row["data_json"]) for row in rows]
    # newest version first, then phase ascending (numeric-aware version sort)
    def sort_key(b: PickupBanner):
        try:
            major, minor = (b.version.split(".") + ["0"])[:2]
            ver = (int(major), int(minor))
        except (ValueError, AttributeError):
            ver = (0, 0)
        return (-ver[0], -ver[1], b.phase or 0)

    return sorted(banners, key=sort_key)
