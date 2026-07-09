"""Build → final stats — a faithful port of ``computeStats`` in build.ts.

WuWa rule: %-stats boost the (character + weapon) base; flats add on top.
``compute_stats`` takes ``extra`` as an already-resolved list of ``(key, value)``
buff deltas — the free-text weapon/sonata parsers that *produce* those deltas
live in the buff-semantics layer (``sim_buff`` / A2), keeping this module numeric.

Inputs ``reso`` / ``weapon`` are the stored catalog JSON shapes (datamine-3.5.0):
  reso["stat_curves"] = {"Life"|"Atk"|"Def"|"Crit"|"CritDamage": [{"level","value"}]}
  weapon["properties"] = [{"curve":[…]}, {"name","curve":[…]}]  # [0]=ATK, [1]=sub%
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

# Every stat the engine tracks; a computed stats dict always has all of them.
STAT_KEYS: tuple[str, ...] = (
    "hp", "atk", "def",
    "hpPct", "atkPct", "defPct",
    "crit", "critDmg", "energyRegen", "healing",
    "basicDmg", "heavyDmg", "skillDmg", "liberationDmg",
    "glacioDmg", "fusionDmg", "electroDmg", "aeroDmg", "spectroDmg", "havocDmg",
)

Buff = tuple[str, float]  # (StatKey, value)


def empty_stats() -> dict[str, float]:
    return {k: 0.0 for k in STAT_KEYS}


# --- Build model -------------------------------------------------------------
@dataclass
class EchoBuild:
    echo_id: str
    cost: int
    grade: int  # 1-5 star
    level: int  # 0-25
    main: str  # StatKey
    subs: list[Buff] = field(default_factory=list)  # [(key, value), …]


@dataclass
class ResonatorBuild:
    level: int = 90  # 1-90
    weapon_id: str | None = None
    weapon_level: int = 90  # 1-90
    weapon_rank: int = 1  # 1-5
    echoes: list[EchoBuild | None] = field(default_factory=lambda: [None] * 5)


@dataclass
class EchoMainOpt:
    key: str
    max: float


@dataclass
class GameConfig:
    cost_budget: int
    main: dict[str, list[EchoMainOpt]]  # cost -> main-stat options (max at L25)
    sub: list[dict[str, Any]] = field(default_factory=list)  # sub-stat pool
    sub_slots: dict[str, int] = field(default_factory=dict)  # grade -> slots


def echo_main_options(config: GameConfig, cost: int) -> list[EchoMainOpt]:
    return config.main.get(str(cost), [])


def sub_max(config: GameConfig, key: str) -> float:
    for s in config.sub:
        if s.get("key") == key:
            return s.get("max", 0)
    return 0


def sub_slots(config: GameConfig, grade: int) -> int:
    return config.sub_slots.get(str(grade), 0)


# main stat value at a given echo level (0-25), linear from ~14% of max at L0.
def echo_main_value(max_val: float, level: float) -> float:
    t = max(0, min(25, level)) / 25
    return max_val * (0.14 + 0.86 * t)


def curve_at(curve: Sequence[Mapping[str, Any]] | None, level: int) -> float:
    """Value at ``level`` from a datamine level curve; falls back to the last row."""
    if not curve:
        return 0
    for c in curve:
        if c.get("level") == level:
            return c.get("value", 0) or 0
    return curve[-1].get("value", 0) or 0


def build_cost(build: ResonatorBuild) -> int:
    return sum((e.cost if e else 0) for e in build.echoes)


def _curves(reso: Any) -> Mapping[str, Any]:
    sc = reso.get("stat_curves") if isinstance(reso, Mapping) else getattr(reso, "stat_curves", None)
    return sc or {}


def _properties(weapon: Any) -> Sequence[Mapping[str, Any]] | None:
    if not weapon:
        return None
    props = weapon.get("properties") if isinstance(weapon, Mapping) else getattr(weapon, "properties", None)
    return props or None


def compute_stats(
    reso: Any,
    weapon: Any,
    build: ResonatorBuild,
    config: GameConfig | None,
    extra: Sequence[Buff] = (),
) -> dict[str, float]:
    """Assemble a build into final stats (sonata sets + weapon passives arrive via ``extra``)."""
    out = empty_stats()
    curves = _curves(reso)
    base_hp = curve_at(curves.get("Life"), build.level)
    base_atk = curve_at(curves.get("Atk"), build.level)
    base_def = curve_at(curves.get("Def"), build.level)
    out["crit"] = curve_at(curves.get("Crit"), build.level) or 5
    out["critDmg"] = curve_at(curves.get("CritDamage"), build.level) or 150
    out["energyRegen"] = 100

    # weapon: property[0] is the main ATK, property[1] the sub-stat (a %)
    weapon_atk = 0.0
    pct = {"hpPct": 0.0, "atkPct": 0.0, "defPct": 0.0}
    flat = {"hp": 0.0, "atk": 0.0, "def": 0.0}
    props = _properties(weapon)
    if props:
        weapon_atk = curve_at((props[0] or {}).get("curve"), build.weapon_level)
        sub = props[1] if len(props) > 1 else None
        if sub:
            v = curve_at(sub.get("curve"), build.weapon_level)
            name = sub.get("name") or ""
            if "공격력" in name:
                pct["atkPct"] += v
            elif "HP" in name:
                pct["hpPct"] += v
            elif "방어력" in name:
                pct["defPct"] += v
            elif "크리티컬 피해" in name:
                out["critDmg"] += v
            elif "크리티컬" in name:
                out["crit"] += v
            elif "효율" in name:
                out["energyRegen"] += v

    def add_stat(key: str, value: float) -> None:
        if key == "hpPct":
            pct["hpPct"] += value
        elif key == "atkPct":
            pct["atkPct"] += value
        elif key == "defPct":
            pct["defPct"] += value
        elif key == "hp":
            flat["hp"] += value
        elif key == "atk":
            flat["atk"] += value
        elif key == "def":
            flat["def"] += value
        else:
            out[key] += value

    for e in build.echoes:
        if not e:
            continue
        opt = None
        if config:
            for o in echo_main_options(config, e.cost):
                if o.key == e.main:
                    opt = o
                    break
        if opt:
            add_stat(e.main, echo_main_value(opt.max, e.level))
        for key, val in e.subs:
            add_stat(key, val)
    for key, val in extra:  # sonata sets + weapon passive buffs (from caller)
        add_stat(key, val)

    out["hp"] = base_hp * (1 + pct["hpPct"] / 100) + flat["hp"]
    out["atk"] = (base_atk + weapon_atk) * (1 + pct["atkPct"] / 100) + flat["atk"]
    out["def"] = base_def * (1 + pct["defPct"] / 100) + flat["def"]
    return out
