"""Catalog → engine glue: read the datamine-sourced catalog and drive the math.

The heavy data (per-level ``stat_curves`` / weapon ``properties`` / skill ``rates``)
lives in the ``data/catalog/*.json`` files (datamine-3.5.0), in the exact shapes
``stats.compute_stats`` consumes. This module indexes those blobs (via the
``catalog.load_codex_*`` readers) and exposes ``character_damages`` — the backend
twin of the frontend TeamBuilder's per-skill damage list.

Resolved buff deltas (sonata sets + weapon passives) arrive via ``extra``; the
free-text parsers that derive them are the buff-semantics layer (``sim_buff`` / A2).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence

from .buffs import active_set_bonuses, weapon_buffs
from .formula import (
    ELEMENT_ANOMALY,
    DamageOpts,
    anomaly_damage,
    anomaly_def_reduce,
    skill_damage,
    tune_break_damage,
)
from .stats import Buff, EchoMainOpt, GameConfig, ResonatorBuild, compute_stats


def to_game_config(echo_stats: Mapping[str, Any]) -> GameConfig:
    """Build a typed :class:`GameConfig` from the ``echo_stats`` blob (pure; DB-free)."""
    main = {
        str(cost): [EchoMainOpt(o["key"], o["max"]) for o in (opts or [])]
        for cost, opts in (echo_stats.get("main") or {}).items()
    }
    return GameConfig(
        cost_budget=echo_stats.get("costBudget", 12),
        main=main,
        sub=echo_stats.get("sub", []),
        sub_slots=echo_stats.get("subSlots", {}),
    )


def rate_at(rates: Sequence[Any], level: int) -> float:
    """Skill multiplier at a level (1-based); ``rates[level-1]`` clamped, percent-parsed."""
    if not rates:
        return 0.0
    idx = min(max(level - 1, 0), len(rates) - 1)
    try:
        return float(str(rates[idx]).replace("%", ""))
    except (TypeError, ValueError):
        return 0.0


@dataclass
class EngineData:
    """Indexed engine inputs loaded once from the DB."""

    config: GameConfig
    anomaly: dict | None
    tune_break: dict | None = None
    resonators_by_id: dict[str, dict] = field(default_factory=dict)
    weapons_by_id: dict[str, dict] = field(default_factory=dict)
    echoes_by_id: dict[str, dict] = field(default_factory=dict)
    sonata_by_name: dict[str, dict] = field(default_factory=dict)


def load_engine_data() -> EngineData:
    """Load + index every combat table (requires a DB connection)."""
    # Imported lazily so the pure math/loader helpers stay usable without a DB.
    from ..catalog import (
        load_codex_echoes,
        load_codex_resonators,
        load_codex_weapons,
        load_sonata_sets,
    )
    from ..content import load_game_config

    cfg = load_game_config()
    return EngineData(
        config=to_game_config(cfg.get("echo_stats") or {}),
        anomaly=cfg.get("anomaly"),
        tune_break=cfg.get("tune_break"),
        resonators_by_id={str(r.get("id")): r for r in load_codex_resonators()},
        weapons_by_id={str(w.get("id")): w for w in load_codex_weapons()},
        echoes_by_id={str(e.get("id")): e for e in load_codex_echoes()},
        sonata_by_name={s.get("name_ko"): s for s in load_sonata_sets()},
    )


def resolve_buffs(
    data: EngineData, build: ResonatorBuild, full_uptime: bool = False
) -> tuple[list[Buff], float]:
    """Auto-derive ``extra`` stat deltas + boost from sonata sets & weapon passive.

    Mirrors the frontend: the dominant sonata set's always-on effects + the weapon's
    always-on buffs apply unconditionally; conditional buffs and the weapon boost %
    apply only under the ``full_uptime`` ("풀 업타임") assumption.
    """
    extra: list[Buff] = []
    active = active_set_bonuses(
        build,
        lambda eid: (data.echoes_by_id.get(str(eid)) or {}).get("sonata") or [],
        data.sonata_by_name,
    )
    if active:
        extra.extend(active["bonuses"])
    boost = 0.0
    weapon = data.weapons_by_id.get(build.weapon_id) if build.weapon_id else None
    if weapon:
        wb = weapon_buffs(weapon, build.weapon_rank)
        extra.extend(wb["always"])
        if full_uptime:
            extra.extend(wb["conditional"])
            boost = wb["boost"]
    return extra, boost


def character_damages(
    data: EngineData,
    reso_id: str | int,
    build: ResonatorBuild,
    opts: DamageOpts | None = None,
    skill_levels: Mapping[int, int] | None = None,
    extra: Sequence[Buff] | None = None,
    extra_add: Sequence[Buff] | None = None,
    full_uptime: bool = False,
) -> dict:
    """Final stats + per-skill damage for one character — mirrors the frontend list.

    ``skill_levels`` maps a skill's index (in the resonator's ``skills``) to its
    level (1-10); unspecified skills default to Lv.10. When ``extra`` is ``None``,
    sonata/weapon buffs are auto-resolved (see :func:`resolve_buffs`); pass an
    explicit list (even empty) to override. ``extra_add`` is appended on top of
    whichever ``extra`` is used — the seam for shared team buffs that support
    members grant the whole party. ``full_uptime`` includes conditional weapon
    buffs + boost.
    """
    reso = data.resonators_by_id.get(str(reso_id))
    if reso is None:
        raise KeyError(f"unknown resonator id: {reso_id}")
    weapon = data.weapons_by_id.get(build.weapon_id) if build.weapon_id else None

    resolved_boost = 0.0
    if extra is None:
        extra, resolved_boost = resolve_buffs(data, build, full_uptime)
    if extra_add:
        extra = list(extra) + list(extra_add)
    stats = compute_stats(reso, weapon, build, data.config, extra=extra)

    o = opts or DamageOpts()
    if resolved_boost:
        o = replace(o, boost=o.boost + resolved_boost)

    element = reso.get("element")
    levels = skill_levels or {}
    skills: list[dict] = []
    for i, s in enumerate(reso.get("skills") or []):
        dmgs = s.get("damage") or []
        if not dmgs:
            continue
        lv = levels.get(i, 10)
        mult = sum(rate_at(d.get("rates") or [], lv) for d in dmgs)
        dmg = skill_damage(stats, mult, element, s.get("SkillType"), o)
        if dmg > 0:
            skills.append(
                {"name": s.get("SkillName") or "", "type": s.get("SkillType") or "", "level": lv, "dmg": dmg}
            )
    return {"stats": stats, "skills": skills}


# Fixed reference conditions for the situational damage sources, matching the
# frontend's former per-character panel defaults: full anomaly stacks (10, one
# occurrence) and the concerto-break reference multiplier. These are reported
# alongside the rotation — never folded into it — because they only apply in
# anomaly/break-focused play.
_ANOMALY_STACKS = 10
_ANOMALY_OCCURRENCES = 1
_TUNE_DEFAULT_MULT = 16.0  # ×100 → multiplier_pct; overridden by game_config tune_break


def member_extra_damages(
    data: EngineData,
    element: str | None,
    stats: Mapping[str, float],
    opts: DamageOpts | None = None,
) -> dict:
    """Situational damage for one member: elemental anomaly (이상) + tune break (조화도 파괴).

    The anomaly type is auto-picked from ``element`` (debuff-type 암흑 yields no
    direct hit, only a DEF-down figure). Tune break uses the catalog's default
    concerto multiplier. Both are evaluated at the same ``opts`` the skills use so
    the numbers stay consistent, and neither is added to the rotation total.
    """
    o = opts or DamageOpts()
    anomaly_type = ELEMENT_ANOMALY.get(element or "")
    anom_dmg = 0.0
    anom_def_down = 0.0
    if anomaly_type and data.anomaly:
        mode = ((data.anomaly.get("types") or {}).get(anomaly_type) or {}).get("mode")
        if mode == "debuff":
            anom_def_down = anomaly_def_reduce(data.anomaly, anomaly_type, _ANOMALY_STACKS)
        else:
            anom_dmg = anomaly_damage(
                data.anomaly, anomaly_type, _ANOMALY_STACKS, stats, o,
                occurrences=_ANOMALY_OCCURRENCES,
            )
    mult = float((data.tune_break or {}).get("defaultMultiplier", _TUNE_DEFAULT_MULT)) * 100
    tune_dmg = tune_break_damage(
        mult, o, crit_rate=stats.get("crit", 0.0), crit_dmg=stats.get("critDmg", 0.0)
    )
    return {
        "anomaly_type": anomaly_type,
        "anomaly_dmg": anom_dmg,
        "anomaly_def_down": anom_def_down,
        "tune_break_dmg": tune_dmg,
    }
