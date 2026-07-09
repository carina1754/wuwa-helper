"""Real-account OCR snapshot → engine build → ABSOLUTE damage.

The differentiator vs phro.love: phro assumes default echo sub-stat distributions
(relative comparison); we feed the player's REAL measured echo mains + subs (from
the vision OCR :class:`CharacterSnapshot`) into the engine, so the numbers are the
player's own — "내 실제 빌드 기준" absolute damage.

Echo MAIN values are deterministic (cost + level → fixed), so only the main's stat
KEY is read from OCR and the engine recomputes the exact value. Echo SUBS are
account-random, so their measured values are used verbatim — that is the whole
point. Sonata sets come from the OCR ``set_name`` on each echo.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..models import CharacterSnapshot
from .buffs import sonata_bonuses_from_counts, weapon_buffs
from .formula import ELEMENT_DMG_KEY, DamageOpts, skill_type_dmg_key
from .loader import EngineData, character_damages
from .stats import Buff, EchoBuild, ResonatorBuild, build_cost


def parse_stat_value(raw: str | None) -> float | None:
    """"12.6%" / "1,050" / "150" → float; ``None`` if unparseable."""
    if raw is None:
        return None
    t = str(raw).replace("%", "").replace(",", "").strip()
    try:
        return float(t)
    except ValueError:
        return None


def _is_percent(name: str, raw: str | None) -> bool:
    return "%" in (raw or "") or name.strip().endswith("%")


def stat_key_from_ko(name: str | None, raw_value: str | None = None) -> str | None:
    """Korean stat label → engine stat key (echo main/sub). ``None`` if unknown.

    ATK/HP/DEF flat vs percent is decided by a ``%`` in the value or name — the
    engine tracks ``atk``/``atkPct`` (etc.) as distinct keys.
    """
    if not name:
        return None
    n = name.strip()
    for elem, key in ELEMENT_DMG_KEY.items():  # 응결/용융/… 피해 보너스
        if elem in n and "피해" in n:
            return key
    if "피해" in n:  # 일반 공격/강공격/공명 스킬/공명 해방 피해 보너스
        st = skill_type_dmg_key(n)
        if st:
            return st
    if "크리티컬 피해" in n or "치명타 피해" in n:
        return "critDmg"
    if "크리티컬" in n or "치명" in n:
        return "crit"
    if "효율" in n:  # 공명 효율
        return "energyRegen"
    if "치료" in n or "치유" in n:
        return "healing"
    pct = _is_percent(n, raw_value)
    if "공격력" in n:
        return "atkPct" if pct else "atk"
    if "방어력" in n:
        return "defPct" if pct else "def"
    if "생명력" in n or "체력" in n or "HP" in n:
        return "hpPct" if pct else "hp"
    return None


def _resolve_id(by_id: dict[str, dict], name: str | None) -> str | None:
    """Match a Korean display name to a catalog id: exact → space-insensitive → substring."""
    if not name:
        return None
    target = name.strip()
    norm = target.replace(" ", "")
    predicates = (
        lambda nm: nm == target,
        lambda nm: nm.replace(" ", "") == norm,
        lambda nm: bool(nm) and (nm in target or target in nm),
    )
    for want in predicates:
        for _id, item in by_id.items():
            if want((item.get("name") or "").strip()):
                return _id
    return None


def resolve_reso_id(data: EngineData, name: str | None) -> str | None:
    return _resolve_id(data.resonators_by_id, name)


def resolve_weapon_id(data: EngineData, name: str | None) -> str | None:
    return _resolve_id(data.weapons_by_id, name)


@dataclass
class SnapshotBuild:
    reso_id: str | None
    build: ResonatorBuild
    set_counts: dict[str, int]
    unresolved: list[str]  # OCR labels the mapper couldn't place (transparency)


def snapshot_to_build(data: EngineData, snap: CharacterSnapshot) -> SnapshotBuild:
    """Map a real-account snapshot onto an engine :class:`ResonatorBuild`."""
    unresolved: list[str] = []
    reso_id = resolve_reso_id(data, snap.character_name)
    if snap.character_name and reso_id is None:
        unresolved.append(f"character:{snap.character_name}")

    weapon_id: str | None = None
    weapon_level, weapon_rank = 90, 1
    if snap.weapon:
        weapon_id = resolve_weapon_id(data, snap.weapon.name)
        if snap.weapon.name and weapon_id is None:
            unresolved.append(f"weapon:{snap.weapon.name}")
        weapon_level = snap.weapon.level or 90
        weapon_rank = snap.weapon.rank or 1

    echoes: list[EchoBuild | None] = [None] * 5
    set_counts: dict[str, int] = {}
    for i, item in enumerate(snap.echoes[:5]):
        main_key = stat_key_from_ko(item.main_stat)
        if item.main_stat and main_key is None:
            unresolved.append(f"main:{item.main_stat}")
        subs: list[Buff] = []
        for sub in item.sub_stats:
            key = stat_key_from_ko(sub.name, sub.value)
            val = parse_stat_value(sub.value)
            if key is None or val is None:
                unresolved.append(f"sub:{sub.name}={sub.value}")
                continue
            subs.append((key, val))
        echoes[i] = EchoBuild(
            echo_id="",  # stats need only cost/level/main/subs; sonata comes from set_name
            cost=item.cost or 0,
            grade=5,
            level=item.level if item.level is not None else 25,
            main=main_key or "atkPct",
            subs=subs,
        )
        if item.set_name:
            set_counts[item.set_name] = set_counts.get(item.set_name, 0) + 1

    build = ResonatorBuild(
        level=snap.character_level or 90,
        weapon_id=weapon_id,
        weapon_level=weapon_level,
        weapon_rank=weapon_rank,
        echoes=echoes,
    )
    return SnapshotBuild(reso_id, build, set_counts, unresolved)


def snapshot_extra(
    data: EngineData, sb: SnapshotBuild, full_uptime: bool = False
) -> tuple[list[Buff], float, str | None]:
    """Resolve buff deltas + boost from the OCR sonata sets and the equipped weapon."""
    extra: list[Buff] = []
    active = sonata_bonuses_from_counts(sb.set_counts, data.sonata_by_name)
    if active:
        extra.extend(active["bonuses"])
    boost = 0.0
    weapon = data.weapons_by_id.get(sb.build.weapon_id) if sb.build.weapon_id else None
    if weapon:
        wb = weapon_buffs(weapon, sb.build.weapon_rank)
        extra.extend(wb["always"])
        if full_uptime:
            extra.extend(wb["conditional"])
            boost = wb["boost"]
    return extra, boost, (active["name"] if active else None)


def snapshot_damage(
    data: EngineData,
    snap: CharacterSnapshot,
    opts: DamageOpts | None = None,
    skill_levels: dict[int, int] | None = None,
    full_uptime: bool = False,
) -> dict:
    """Absolute per-skill damage for one real-account snapshot.

    Raises ``KeyError`` if the character name can't be matched to a resonator.
    """
    sb = snapshot_to_build(data, snap)
    if sb.reso_id is None:
        raise KeyError(f"unknown resonator: {snap.character_name}")
    extra, boost, set_name = snapshot_extra(data, sb, full_uptime)
    o = opts or DamageOpts()
    if boost:
        o = replace(o, boost=o.boost + boost)
    res = character_damages(
        data, sb.reso_id, sb.build, opts=o, skill_levels=skill_levels, extra=extra
    )
    reso = data.resonators_by_id[sb.reso_id]
    return {
        "reso_id": sb.reso_id,
        "name": reso.get("name") or reso.get("nickname"),
        "element": reso.get("element"),
        "set_name": set_name,
        "stats": res["stats"],
        "skills": res["skills"],
        "total": sum(s["dmg"] for s in res["skills"]),
        "cost": build_cost(sb.build),
        "unresolved": sb.unresolved,
    }
