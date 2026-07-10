"""Character-kit TEAM buffs/debuffs → resolved party-wide deltas.

Twin of :mod:`chains` but for **kit** team effects — the buffs a character's
own skills (반주/고유/공명해방/공명회로…) grant to party allies (or the next
character), plus the debuffs they place on the enemy. Data source is the
authoritative catalog file ``data/catalog/team_effects.json``::

    {reso_id: {"name", "element", "effects": [effect, …]}}

Effect kinds (every numeric value is grounded in ``source`` skill text):
  * ``team_stat``    {key, value}            → party-wide ``compute_stats`` delta
  * ``team_boost``   {value, element}        → ``opts.boost`` (element-filtered)
  * ``enemy_debuff`` {sub, value, element}   → ``opts.res_shred|def_reduce|dmg_taken``
  * ``note``         {reason, text}          → transparency only (unquantifiable)

``cond`` effects apply only under the SOURCE member's ``full_uptime`` ("풀
업타임"), matching the chain / weapon-passive convention. ``note`` effects are
always surfaced. Element-specific boosts/shreds are filtered by the *receiving*
member's element in the caller (:func:`sim.api.team_calculate`), because
``opts.boost`` / ``opts.res_shred`` are single global scalars in the formula.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .stats import Buff

# team_effects.json lives beside the other catalog files; kits.py sits one dir
# deeper than catalog.py (src/sim/ vs src/), hence parents[2] like chains.py.
_EFFECTS_PATH = Path(__file__).resolve().parents[2] / "data" / "catalog" / "team_effects.json"


@lru_cache(maxsize=1)
def _load_effects() -> dict:
    if not _EFFECTS_PATH.exists():
        return {}
    return json.loads(_EFFECTS_PATH.read_text(encoding="utf-8"))


@dataclass
class KitBoost:
    """A '피해 부스트'(Amplify) delta.

    ``element=None`` and ``skill_type=None`` ⇒ whole-damage global boost.
    ``element`` set ⇒ only members of that element (their whole total is that
    element). ``skill_type`` set (basic|heavy|skill|liberation) ⇒ applies only
    to that skill type, folded per-skill by the engine (not the global bucket).
    """
    value: float  # percent points (opts.boost is 1 + boost/100)
    element: Optional[str] = None
    skill_type: Optional[str] = None  # basic|heavy|skill|liberation


@dataclass
class KitDebuff:
    """An enemy debuff. ``element=None`` ⇒ element-agnostic (applies to everyone)."""
    sub: str  # "res_shred" | "def_reduce" | "dmg_taken"
    value: float  # raw percent number from text (unit conversion is the caller's job)
    element: Optional[str] = None


@dataclass
class KitResolved:
    team_stats: list[Buff] = field(default_factory=list)  # (StatKey, value) party-wide
    team_boosts: list[KitBoost] = field(default_factory=list)
    enemy_debuffs: list[KitDebuff] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def resolve_kit(
    reso_id: str, full_uptime: bool = False, effects: Optional[dict] = None
) -> KitResolved:
    """Resolve one resonator's kit team effects into party-wide deltas."""
    data = effects if effects is not None else _load_effects()
    out = KitResolved()
    entry = data.get(str(reso_id))
    if not entry:
        return out
    for e in entry.get("effects") or []:
        kind = e.get("kind")
        if kind == "note":
            txt = e.get("text") or e.get("source") or ""
            if txt:
                out.notes.append(txt)
            continue
        if e.get("cond") and not full_uptime:
            continue
        if kind == "team_stat":
            key, val = e.get("key"), e.get("value")
            if key and val is not None:
                out.team_stats.append((key, float(val)))
        elif kind == "team_boost":
            val = e.get("value")
            if val is not None:
                out.team_boosts.append(
                    KitBoost(float(val), e.get("element") or None, e.get("skill_type") or None)
                )
        elif kind == "enemy_debuff":
            sub, val = e.get("sub"), e.get("value")
            if sub and val is not None:
                out.enemy_debuffs.append(KitDebuff(sub, float(val), e.get("element") or None))
    return out


# --- readable labels (transparency: show the user what auto-applied) ----------
_STAT_LABEL: dict[str, str] = {
    "atkPct": "공격력", "crit": "크리티컬", "critDmg": "크리티컬 피해",
    "energyRegen": "공명 효율", "hpPct": "HP", "defPct": "방어력",
    "basicDmg": "일반 공격 피해", "heavyDmg": "강공격 피해",
    "skillDmg": "공명 스킬 피해", "liberationDmg": "공명 해방 피해",
    "glacioDmg": "응결 피해", "fusionDmg": "용융 피해", "electroDmg": "전도 피해",
    "aeroDmg": "기류 피해", "spectroDmg": "회절 피해", "havocDmg": "인멸 피해",
}
_DEBUFF_LABEL: dict[str, str] = {
    "res_shred": "저항 감소", "def_reduce": "방어 감소", "dmg_taken": "받는 피해 증가",
}
# skill-type boost buckets → engine damage-bonus key (loader.skill_type_dmg_key
# convention) and a readable Korean label.
BOOST_TYPE_DMGKEY: dict[str, str] = {
    "basic": "basicDmg", "heavy": "heavyDmg", "skill": "skillDmg", "liberation": "liberationDmg",
}
_BOOST_TYPE_LABEL: dict[str, str] = {
    "basic": "일반 공격", "heavy": "강공격", "skill": "공명 스킬", "liberation": "공명 해방",
}


def stat_label(key: str) -> str:
    return _STAT_LABEL.get(key, key)


def boost_label(element: Optional[str], skill_type: Optional[str]) -> str:
    """Readable label for a '피해 부스트' bucket (element / skill-type / global)."""
    if skill_type:
        return f"{_BOOST_TYPE_LABEL.get(skill_type, skill_type)} 피해 부스트"
    if element:
        return f"{element} 피해 부스트"
    return "전체 피해 부스트"


def debuff_label(sub: str, element: Optional[str]) -> str:
    base = _DEBUFF_LABEL.get(sub, sub)
    if sub == "res_shred" and element:
        return f"{element} {base}"
    return base
