"""Refresh the ``wuwa_*`` tables from the encore.moe API.

Each refresh fetches the route's list, then every detail record, normalizes it,
upserts by game id, and reconciles (drops rows no longer present). Curated
resonator roles come from the static ``_CURATED_ROLE`` map. Run order matters:
resonators first, then echoes (echo filtering needs the resonator names).
"""
from __future__ import annotations

import json

from ..database import get_connection
from ..wutheringgg.refresh import _CURATED_ROLE
from . import client
from .normalize import normalize_echo, normalize_resonator, normalize_weapon

# WeaponType id -> Korean name (fallback; refresh prefers the list's TypeName).
_WTYPE_KO = {1: "브로드소드", 2: "직검", 3: "권총", 4: "권갑", 5: "증폭기"}


def _en_names(route: str, *, use_cache: bool = True) -> dict:
    """id -> English name from the en list (best-effort; names only)."""
    try:
        return {r.get("Id"): r.get("Name") for r in client.fetch_list(route, "en", use_cache=use_cache)}
    except Exception:  # noqa: BLE001 - en names are optional enrichment
        return {}


def refresh_resonators(*, use_cache: bool = True) -> int:
    summaries = client.fetch_list("character", use_cache=use_cache)
    ids = [r["Id"] for r in summaries]
    en = _en_names("character", use_cache=use_cache)
    details = client.fetch_all_details("character", ids, use_cache=use_cache)
    kept: list[int] = []
    with get_connection() as conn:
        for d in details:
            rec = normalize_resonator(d, en.get(d.get("Id")))
            rec["role"] = _CURATED_ROLE.get(rec["id"], "main_dps")
            conn.execute(
                """
                INSERT INTO wuwa_resonator
                    (id, name_ko, name_en, element, weapon_type, rarity, role, data_json, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name_ko=EXCLUDED.name_ko, name_en=EXCLUDED.name_en, element=EXCLUDED.element,
                    weapon_type=EXCLUDED.weapon_type, rarity=EXCLUDED.rarity, role=EXCLUDED.role,
                    data_json=EXCLUDED.data_json, updated_at=now()
                """,
                (
                    rec["id"], rec["name"], rec["name_en"], rec["element"],
                    rec["weapon_type"], rec["rarity"], rec["role"],
                    json.dumps(rec, ensure_ascii=False),
                ),
            )
            kept.append(rec["id"])
        if kept:
            conn.execute("DELETE FROM wuwa_resonator WHERE NOT (id = ANY(%s))", (kept,))
        conn.commit()
    return len(kept)


def refresh_weapons(*, use_cache: bool = True) -> int:
    summaries = client.fetch_list("weapon", use_cache=use_cache)
    ids = [r["Id"] for r in summaries]
    wtype_ko = {r.get("Type"): r.get("TypeName") for r in summaries if r.get("Type") is not None}
    # The weapon detail only carries raw /Game/... asset paths; the list carries a
    # servable absolute icon URL, so take the icon from there.
    icon_map = {r.get("Id"): r.get("Icon") for r in summaries}
    en = _en_names("weapon", use_cache=use_cache)
    details = client.fetch_all_details("weapon", ids, use_cache=use_cache)
    kept: list[str] = []
    with get_connection() as conn:
        for d in details:
            rec = normalize_weapon(d, en.get(d.get("ItemId")))
            rec["weapon_type_ko"] = wtype_ko.get(rec["weapon_type"]) or _WTYPE_KO.get(rec["weapon_type"])
            rec["icon"] = icon_map.get(rec["id"]) or rec["icon"]
            wid = str(rec["id"])
            conn.execute(
                """
                INSERT INTO wuwa_weapon
                    (id, name_ko, name_en, weapon_type, rarity, data_json, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name_ko=EXCLUDED.name_ko, name_en=EXCLUDED.name_en,
                    weapon_type=EXCLUDED.weapon_type, rarity=EXCLUDED.rarity,
                    data_json=EXCLUDED.data_json, updated_at=now()
                """,
                (wid, rec["name_ko"], rec["name_en"], rec.get("weapon_type_ko"), rec["rarity"],
                 json.dumps(rec, ensure_ascii=False)),
            )
            kept.append(wid)
        if kept:
            conn.execute("DELETE FROM wuwa_weapon WHERE NOT (id = ANY(%s))", (kept,))
        conn.commit()
    return len(kept)


def refresh_echoes(*, use_cache: bool = True) -> int:
    summaries = client.fetch_list("echo", use_cache=use_cache)
    ids = [r["Id"] for r in summaries]
    en = _en_names("echo", use_cache=use_cache)
    details = client.fetch_all_details("echo", ids, use_cache=use_cache)
    kept: list[str] = []
    with get_connection() as conn:
        # Character/boss "phantom" entries share the echo route; drop any whose
        # name is a resonator name (resonators are refreshed first).
        reso_names = {r["name_ko"] for r in conn.execute("SELECT name_ko FROM wuwa_resonator").fetchall()}
        for d in details:
            rec = normalize_echo(d, en.get(d.get("ItemId") or d.get("MonsterId")))
            if not rec["name_ko"] or rec["name_ko"] in reso_names:
                continue
            eid = str(rec["id"])
            conn.execute(
                """
                INSERT INTO wuwa_echo
                    (id, name_ko, name_en, cost, rarity, data_json, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    name_ko=EXCLUDED.name_ko, name_en=EXCLUDED.name_en, cost=EXCLUDED.cost,
                    rarity=EXCLUDED.rarity, data_json=EXCLUDED.data_json, updated_at=now()
                """,
                (eid, rec["name_ko"], rec["name_en"], rec["cost"], rec["rarity"],
                 json.dumps(rec, ensure_ascii=False)),
            )
            kept.append(eid)
        if kept:
            conn.execute("DELETE FROM wuwa_echo WHERE NOT (id = ANY(%s))", (kept,))
        conn.commit()
    return len(kept)


def refresh_all(*, use_cache: bool = True) -> dict:
    return {
        "resonators": refresh_resonators(use_cache=use_cache),
        "weapons": refresh_weapons(use_cache=use_cache),
        "echoes": refresh_echoes(use_cache=use_cache),
    }
