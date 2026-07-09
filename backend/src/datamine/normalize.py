from __future__ import annotations

import json

from psycopg import Connection

from .textmap import resolve_text

_ELEMENT_KO = {1: "응결", 2: "용융", 3: "전도", 4: "기류", 5: "회절", 6: "인멸"}
_WEAPON_TYPE_KO = {1: "브로드소드", 2: "직검", 3: "권총", 4: "권갑", 5: "증폭기"}


def _bindata_rows(conn: Connection, table_name: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT data FROM datamine_bindata WHERE table_name = %s", (table_name,))
        return [r["data"] for r in cur.fetchall()]


def build_sim_role_growth(conn: Connection) -> int:
    rows = _bindata_rows(conn, "property/rolepropertygrowth")
    n = 0
    with conn.cursor() as cur:
        for d in rows:
            cur.execute(
                """
                INSERT INTO sim_role_growth (level, breach, atk_ratio, def_ratio, hp_ratio)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (level, breach) DO UPDATE SET
                    atk_ratio = EXCLUDED.atk_ratio,
                    def_ratio = EXCLUDED.def_ratio,
                    hp_ratio = EXCLUDED.hp_ratio
                """,
                (d["Level"], d["BreachLevel"], d["AtkRatio"], d["DefRatio"], d["LifeMaxRatio"]),
            )
            n += 1
    conn.commit()
    return n


def _is_playable(d: dict) -> bool:
    return d.get("RoleType") == 1 and not d.get("IsTrial") and (d.get("QualityId") or 0) >= 4


def build_sim_character(conn: Connection) -> int:
    roles = [d for d in _bindata_rows(conn, "role/roleinfo") if _is_playable(d)]
    base_by_id = {
        d["Id"]: d
        for d in _bindata_rows(conn, "property/baseproperty")
        if d.get("Lv") == 1
    }
    n = 0
    with conn.cursor() as cur:
        for r in roles:
            base = base_by_id.get(r.get("PropertyId") or r["Id"])
            if base is None:
                continue
            rec = {
                "id": r["Id"],
                "name_ko": resolve_text(conn, "ko", r.get("Name") or ""),
                "name_en": resolve_text(conn, "en", r.get("Name") or ""),
                "rarity": r.get("QualityId"),
                "element_id": r.get("ElementId"),
                "element_ko": _ELEMENT_KO.get(r.get("ElementId")),
                "weapon_type": r.get("WeaponType"),
                "weapon_type_ko": _WEAPON_TYPE_KO.get(r.get("WeaponType")),
                "max_level": r.get("MaxLevel"),
                "base_atk": base["Atk"],
                "base_hp": base["LifeMax"],
                "base_def": base["Def"],
                "base_crit": base["Crit"] / 100.0,
                "base_crit_dmg": base["CritDamage"] / 100.0,
                "skill_id": r.get("SkillId"),
                "skill_tree_group_id": r.get("SkillTreeGroupId"),
                "resonant_chain_group_id": r.get("ResonantChainGroupId"),
            }
            cur.execute(
                """
                INSERT INTO sim_character (
                    id, name_ko, name_en, rarity, element_id, element_ko,
                    weapon_type, weapon_type_ko, max_level,
                    base_atk, base_hp, base_def, base_crit, base_crit_dmg,
                    skill_id, skill_tree_group_id, resonant_chain_group_id,
                    data_json, updated_at
                ) VALUES (
                    %(id)s, %(name_ko)s, %(name_en)s, %(rarity)s, %(element_id)s, %(element_ko)s,
                    %(weapon_type)s, %(weapon_type_ko)s, %(max_level)s,
                    %(base_atk)s, %(base_hp)s, %(base_def)s, %(base_crit)s, %(base_crit_dmg)s,
                    %(skill_id)s, %(skill_tree_group_id)s, %(resonant_chain_group_id)s,
                    %(data_json)s, now()
                )
                ON CONFLICT (id) DO UPDATE SET
                    name_ko = EXCLUDED.name_ko, name_en = EXCLUDED.name_en, rarity = EXCLUDED.rarity,
                    element_id = EXCLUDED.element_id, element_ko = EXCLUDED.element_ko,
                    weapon_type = EXCLUDED.weapon_type, weapon_type_ko = EXCLUDED.weapon_type_ko,
                    max_level = EXCLUDED.max_level, base_atk = EXCLUDED.base_atk, base_hp = EXCLUDED.base_hp,
                    base_def = EXCLUDED.base_def, base_crit = EXCLUDED.base_crit,
                    base_crit_dmg = EXCLUDED.base_crit_dmg, skill_id = EXCLUDED.skill_id,
                    skill_tree_group_id = EXCLUDED.skill_tree_group_id,
                    resonant_chain_group_id = EXCLUDED.resonant_chain_group_id,
                    data_json = EXCLUDED.data_json, updated_at = now()
                """,
                {**rec, "data_json": json.dumps(rec, ensure_ascii=False)},
            )
            n += 1
    conn.commit()
    return n
