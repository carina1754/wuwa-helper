"""Catalog helpers still sourced from Namuwiki: sonata sets + pickup banners.

The rich resonator/weapon/echo dataset now comes from the datamine catalog files
(``data/catalog/*.json``, loaded by the ``load_codex_*`` helpers here). Two things
aren't in that dataset and are still crawled from Namuwiki:

* **sonata sets** — crest icon + 2/5-set bonus text (the codex sonata filter).
* **pickup banners** — which unit ran on which version/phase. Avatars and weapon
  icons for those banners are enriched from that same datamine catalog (matched
  by Korean name), falling back to the banner's own extracted art when unmatched.

Everything is stored as a data_json blob keyed by a stable hash so the schema can
evolve without migrations.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from .database import get_connection
from .media import ensure_catalog_image
from .models import PickupBanner
from .namu import echoes as namu_echoes
from .namu.banners import parse_banner_history
from .namu.client import fetch_page, sub_page


def _hash_id(prefix: str, name_ko: str) -> str:
    return prefix + hashlib.sha1(name_ko.encode("utf-8")).hexdigest()[:12]


def _norm_name(name: str | None) -> str:
    """Normalize a Korean name for cross-source matching (drop whitespace and
    middle-dot variants) — mirrors the frontend's resonator name matching."""
    return re.sub(r"[\s·・]", "", name or "")


# --- Sonata sets (Namuwiki-sourced: crest icon + 2/5-set bonus) ---------------
def refresh_sonata_sets() -> int:
    """Crawl the sonata set definitions from Namuwiki, cache crest icons, store.

    Returns the number of sets written. (Individual echoes now come from the
    datamine catalog (``echoes.json``); only the set definitions remain
    Namuwiki-sourced.)
    """
    sonata_sets = namu_echoes.parse_sonata_sets(fetch_page(sub_page("데이터 스테이션")))
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
        conn.commit()
    return len(sonata_sets)


# --- Datamine catalog artifacts (files = runtime source of truth) -------------
# The sim/codex catalog (resonators, weapons, echoes, sonata sets) is served from
# versioned JSON files under data/catalog/, generated from the datamine
# (WutheringWaves_Data-3.5). These files are the runtime source of truth; the
# wuwa_*/sonata_set tables are retained only for rollback and the (serving-
# irrelevant) refresh writers. Regenerate with scripts/export_catalog_to_files.py.
# Memoized -> data changes require a process restart (same model as the sim _ENGINE).
_CATALOG_DIR = Path(__file__).resolve().parents[1] / "data" / "catalog"


@lru_cache(maxsize=None)
def _load_catalog_file(name: str) -> tuple[dict, ...]:
    """Load one catalog artifact as an immutable tuple of dicts (shared, read-only).

    Files are written in the same order the old ORDER BY queries produced, so
    file-primary serving is a byte-faithful, zero-regression swap.
    """
    path = _CATALOG_DIR / f"{name}.json"
    return tuple(json.loads(path.read_text(encoding="utf-8")))


def _maybe_int(value):
    """Preserve legacy integer typing for numeric ids without failing on TEXT ids."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def load_sonata_sets() -> list[dict]:
    return list(_load_catalog_file("sonata_sets"))


# --- Codex: rich datamine dataset (served from data/catalog/*.json) ------------
def load_codex_resonators() -> list[dict]:
    return list(_load_catalog_file("resonators"))


def load_codex_weapons() -> list[dict]:
    return list(_load_catalog_file("weapons"))


def load_codex_echoes() -> list[dict]:
    return list(_load_catalog_file("echoes"))


# --- Pickup banners (characters + weapons per version/phase) ------------------
# Banner history (which unit ran when) is crawled from Namuwiki 튜닝 pages and
# merged by (version, phase). Character avatars and weapon icons are enriched
# from the datamine catalog (resonators / weapons) by Korean-name match;
# unmatched names (e.g. an unreleased unit) fall back to the banner's own
# extracted art / no icon.
def _char_avatar_source(name_ko: str, icons: list[dict] | None) -> str | None:
    for icon in icons or []:
        alt = icon.get("alt") or ""
        if name_ko in alt and "아이콘" not in alt and "패턴" not in alt and "로고" not in alt:
            return icon.get("src")
    return None


def _resonator_by_name() -> dict[str, dict]:
    """Map normalized resonator KO name -> {id, image} for pickup avatars."""
    out: dict[str, dict] = {}
    for r in load_codex_resonators():
        out[_norm_name(r.get("name"))] = {"id": _maybe_int(r.get("id")), "image": r.get("image")}
    return out


def _weapon_by_name() -> dict[str, dict]:
    """Map normalized weapon KO name -> {icon, rarity, weapon_type} for pickup weapons."""
    out: dict[str, dict] = {}
    for w in load_codex_weapons():
        out[_norm_name(w.get("name_ko"))] = {
            "icon": w.get("icon"),
            "rarity": w.get("rarity"),
            "weapon_type": w.get("weapon_type_ko") or w.get("weapon_type"),
        }
    return out


def _match_resonator(name: str, by_name: dict[str, dict]) -> dict | None:
    """Normalized match, then retry on the pre-middle-dot base name (e.g. the
    pickup title '양양·현령' resolves to the resonator '양양')."""
    hit = by_name.get(_norm_name(name))
    if hit:
        return hit
    base = re.split(r"[·・]", name, 1)[0]
    if base and base != name:
        return by_name.get(_norm_name(base))
    return None


# The master 튜닝 page details only the current era (3.x); older eras live in
# per-era sub-articles. Collab banners live on their own pages and run
# concurrently with a version's regular banners, so they must not merge into the
# same (version, phase) slot -- they are tracked separately (is_collab=True).
_BANNER_ERAS = (None, "1.X 버전", "2.X 버전")


def _all_banner_history(page: str, kind: str) -> list[dict]:
    banners: list[dict] = []
    for era in _BANNER_ERAS:
        title = sub_page("튜닝", page) if era is None else sub_page("튜닝", page, era)
        banners.extend(parse_banner_history(fetch_page(title), kind))
    return banners


def _collab_banner_history(page: str, kind: str) -> list[dict]:
    return parse_banner_history(fetch_page(sub_page("튜닝", page)), kind)


def refresh_pickup_banners() -> int:
    """Crawl character + weapon banner history (regular + collab), merge, store."""
    char_banners = _all_banner_history("캐릭터 이벤트 튜닝", "character")
    weapon_banners = _all_banner_history("무기 이벤트 튜닝", "weapon")
    char_collab = _collab_banner_history("캐릭터 콜라보 튜닝", "character")
    weapon_collab = _collab_banner_history("무기 콜라보 튜닝", "weapon")
    resonator_by_name = _resonator_by_name()
    weapon_by_name = _weapon_by_name()

    merged: dict[tuple, dict] = {}

    def slot(banner: dict, is_collab: bool) -> dict:
        key = (banner["version"], banner.get("phase"), is_collab)
        return merged.setdefault(
            key,
            {
                "version": banner["version"],
                "phase": banner.get("phase"),
                "banner_name": banner.get("banner_name"),
                "is_rerun": banner.get("is_rerun", False),
                "is_collab": is_collab,
                "characters": [],
                "weapons": [],
                "start_date": banner.get("start_date"),
                "end_date": banner.get("end_date"),
            },
        )

    def add_characters(banners: list[dict], is_collab: bool) -> None:
        for banner in banners:
            entry = slot(banner, is_collab)
            for name in banner.get("items", []):
                reso = _match_resonator(name, resonator_by_name)
                avatar = reso["image"] if reso else None
                if not avatar:
                    cid = _hash_id("c-", name)
                    avatar = ensure_catalog_image(
                        "characters", cid, _char_avatar_source(name, banner.get("icons"))
                    )
                entry["characters"].append(
                    {
                        "name_ko": name,
                        "avatar": avatar,
                        "catalog_id": reso["id"] if reso else None,
                    }
                )

    def add_weapons(banners: list[dict], is_collab: bool) -> None:
        for banner in banners:
            entry = slot(banner, is_collab)
            for name in banner.get("items", []):
                weapon = weapon_by_name.get(_norm_name(name))
                entry["weapons"].append(
                    {
                        "name_ko": name,
                        "icon": weapon["icon"] if weapon else None,
                        "rarity": weapon["rarity"] if weapon else None,
                        "weapon_type": weapon["weapon_type"] if weapon else None,
                    }
                )

    add_characters(char_banners, False)
    add_characters(char_collab, True)
    add_weapons(weapon_banners, False)
    add_weapons(weapon_collab, True)

    with get_connection() as conn:
        conn.execute("DELETE FROM pickup_banners")
        for (version, phase, is_collab), entry in merged.items():
            bid = f"{version}-collab-p{phase}" if is_collab else f"{version}-p{phase}"
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
