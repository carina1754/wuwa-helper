"""Server-side team damage calculation (phro.love-style ``/team-calculate``).

Wraps the engine (:mod:`src.sim.loader`) in a request/response contract so a whole
party can be scored on the server from a single payload. The engine is loaded once
and cached; ``team_calculate`` accepts an optional ``data`` override for testing.

Party-wide effects (e.g. 암흑 −6% DEF shred) are passed as ``party_def_shred`` and
folded into every member's ``def_reduce``. Per-member sonata/weapon buffs are
auto-resolved by the engine (``full_uptime`` toggles conditional weapon buffs).
"""

from __future__ import annotations

from dataclasses import replace

from pydantic import BaseModel, Field

from ..models import CharacterSnapshot
from .chains import resolve_chain
from .formula import ELEMENT_DMG_KEY, DamageOpts
from .kits import (
    BOOST_TYPE_DMGKEY,
    KitBoost,
    KitDebuff,
    boost_label,
    debuff_label,
    resolve_kit,
    stat_label,
)
from .loader import EngineData, character_damages, load_engine_data, member_extra_damages
from .snapshot import snapshot_damage
from .stats import EchoBuild, ResonatorBuild, build_cost


# --- request ----------------------------------------------------------------
class SubIn(BaseModel):
    key: str
    value: float


class EchoIn(BaseModel):
    echo_id: str
    cost: int
    grade: int = 5
    level: int = 25
    main: str
    subs: list[SubIn] = Field(default_factory=list)


class MemberIn(BaseModel):
    reso_id: str
    level: int = 90
    weapon_id: str | None = None
    weapon_level: int = 90
    weapon_rank: int = 1
    echoes: list[EchoIn] = Field(default_factory=list)
    skill_levels: dict[int, int] = Field(default_factory=dict)
    full_uptime: bool = False
    sequence: int = 0  # 공명 사슬 S0-S6 (owned sequence node count)


class OptsIn(BaseModel):
    my_level: int = 90
    enemy_level: int = 90
    enemy_res: float = 0.2
    res_shred: float = 0
    def_ignore: float = 0
    def_reduce: float = 0
    boost: float = 0
    dmg_taken: float = 0
    total_dmg: float = 0
    bonus_pct: float = 0


class TeamCalcRequest(BaseModel):
    members: list[MemberIn]
    opts: OptsIn = Field(default_factory=OptsIn)
    party_def_shred: float = 0  # team-wide DEF reduction (e.g. 암흑 −6%)
    team_buffs: list[SubIn] = Field(default_factory=list)  # shared buffs on every member


# --- response ---------------------------------------------------------------
class SkillOut(BaseModel):
    name: str
    type: str
    level: int
    dmg: float


class MemberOut(BaseModel):
    reso_id: str
    name: str | None = None
    element: str | None = None
    stats: dict[str, float]
    skills: list[SkillOut]
    total: float  # one pass of every listed skill
    cost: int
    sequence: int = 0  # 공명 사슬 S0-S6 applied
    # Effects the sequence contributes but the engine does NOT fold into damage
    # (mechanical / conditional-complex / survivability) — surfaced for transparency.
    chain_notes: list[dict] = Field(default_factory=list)
    # Character-kit TEAM buffs auto-applied to this member (readable, transparency)
    # and this member's own unquantifiable kit team notes.
    applied_team_buffs: list[str] = Field(default_factory=list)
    team_notes: list[str] = Field(default_factory=list)
    # Situational sources — reported for reference, NOT part of ``total``.
    anomaly_type: str | None = None  # 이상 type derived from element (없으면 None)
    anomaly_dmg: float = 0  # 이상 direct damage at full stacks
    anomaly_def_down: float = 0  # 암흑-type debuff: DEF reduction fraction (no direct hit)
    tune_break_dmg: float = 0  # 조화도 파괴 reference damage


class TeamCalcResponse(BaseModel):
    members: list[MemberOut]
    team_total: float


# --- service ----------------------------------------------------------------
_ENGINE: EngineData | None = None


def get_engine() -> EngineData:
    """Load + cache the engine data (one DB read per process)."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = load_engine_data()
    return _ENGINE


def _damage_opts(base: OptsIn, extra_def_reduce: float = 0.0) -> DamageOpts:
    """Map the request opts onto the engine's :class:`DamageOpts`."""
    return DamageOpts(
        my_level=base.my_level,
        enemy_level=base.enemy_level,
        enemy_res=base.enemy_res,
        res_shred=base.res_shred,
        def_ignore=base.def_ignore,
        def_reduce=min(1.0, base.def_reduce + extra_def_reduce),
        boost=base.boost,
        dmg_taken=base.dmg_taken,
        total_dmg=base.total_dmg,
        bonus_pct=base.bonus_pct,
    )


def _echoes(echoes: list[EchoIn]) -> list[EchoBuild | None]:
    out: list[EchoBuild | None] = [None] * 5
    for i, e in enumerate(echoes[:5]):
        out[i] = EchoBuild(
            echo_id=e.echo_id, cost=e.cost, grade=e.grade, level=e.level,
            main=e.main, subs=[(s.key, s.value) for s in e.subs],
        )
    return out


def team_calculate(req: TeamCalcRequest, data: EngineData | None = None) -> TeamCalcResponse:
    """Score every party member and the team total. ``data`` defaults to the cached engine."""
    data = data or get_engine()
    base = req.opts
    req_team_buffs = [(b.key, b.value) for b in req.team_buffs]

    # Pass 1: resolve each member's 공명 사슬 (sequence) AND character-kit team
    # effects. A support buffs/debuffs the whole party, so every member must see
    # the union before being scored. ``team_stat`` deltas apply to everyone (the
    # stat key self-filters by element/type); element-specific boosts (Amplify)
    # and enemy shreds keep their element and are filtered per member in pass 2,
    # because ``opts.boost`` / ``opts.res_shred`` are single global scalars.
    resolved: list[tuple] = []
    chain_team_buffs: list[tuple[str, float]] = []
    kit_team_buffs: list[tuple[str, float]] = []
    party_boosts: list[KitBoost] = []
    party_debuffs: list[KitDebuff] = []
    for m in req.members:
        reso = data.resonators_by_id.get(str(m.reso_id))
        if reso is None:
            raise KeyError(f"unknown resonator id: {m.reso_id}")
        chain = resolve_chain(str(m.reso_id), m.sequence, m.full_uptime, reso.get("element"))
        chain_team_buffs.extend(chain.team_stats)
        kit = resolve_kit(str(m.reso_id), m.full_uptime)
        kit_team_buffs.extend(kit.team_stats)
        party_boosts.extend(kit.team_boosts)
        party_debuffs.extend(kit.enemy_debuffs)
        resolved.append((m, reso, chain, kit))
    all_team_buffs = req_team_buffs + chain_team_buffs + kit_team_buffs

    # Pass 2: score every member with self effects + all team buffs, folding this
    # member's element-matched party boost/debuff scalars into its opts.
    members_out: list[MemberOut] = []
    team_total = 0.0
    for m, reso, chain, kit in resolved:
        element = reso.get("element")
        # Whole-damage boosts (global + this member's element) fold into the
        # single opts.boost bucket; skill-type-specific boosts go into a per-type
        # map the engine applies only to matching skills.
        boost_add = sum(b.value for b in party_boosts
                        if b.skill_type is None and b.element in (None, element))
        type_boosts: dict[str, float] = {}
        for b in party_boosts:
            if b.skill_type and b.value and b.element in (None, element):
                dk = BOOST_TYPE_DMGKEY.get(b.skill_type)
                if dk:
                    type_boosts[dk] = type_boosts.get(dk, 0.0) + b.value
        rs_add = sum(d.value for d in party_debuffs
                     if d.sub == "res_shred" and d.element in (None, element))
        dr_add = sum(d.value for d in party_debuffs
                     if d.sub == "def_reduce" and d.element in (None, element))
        dt_add = sum(d.value for d in party_debuffs
                     if d.sub == "dmg_taken" and d.element in (None, element))
        base_opts = _damage_opts(base, req.party_def_shred)
        opts = replace(
            base_opts,
            my_level=m.level,
            boost=base_opts.boost + boost_add,
            res_shred=base_opts.res_shred + rs_add / 100,
            def_reduce=min(0.95, base_opts.def_reduce + dr_add / 100),
            dmg_taken=base_opts.dmg_taken + dt_add,
        )
        build = ResonatorBuild(
            level=m.level, weapon_id=m.weapon_id, weapon_level=m.weapon_level,
            weapon_rank=m.weapon_rank, echoes=_echoes(m.echoes),
        )
        res = character_damages(
            data, m.reso_id, build, opts=opts,
            skill_levels=m.skill_levels, extra_add=all_team_buffs or None,
            full_uptime=m.full_uptime, chain=chain,
            type_boosts=type_boosts or None,
        )
        total = sum(s["dmg"] for s in res["skills"])
        team_total += total
        extra = member_extra_damages(data, element, res["stats"], opts)
        members_out.append(
            MemberOut(
                reso_id=str(m.reso_id),
                name=reso.get("name") or reso.get("nickname"),
                element=element,
                stats={k: round(v, 2) for k, v in res["stats"].items()},
                skills=[SkillOut(**s) for s in res["skills"]],
                total=total,
                cost=build_cost(build),
                sequence=m.sequence,
                chain_notes=res.get("chain_notes") or [],
                applied_team_buffs=_format_applied(all_team_buffs, party_boosts, party_debuffs, element),
                team_notes=kit.notes,
                anomaly_type=extra["anomaly_type"],
                anomaly_dmg=round(extra["anomaly_dmg"], 2),
                anomaly_def_down=round(extra["anomaly_def_down"], 4),
                tune_break_dmg=round(extra["tune_break_dmg"], 2),
            )
        )
    return TeamCalcResponse(members=members_out, team_total=team_total)


def _format_applied(
    team_buffs: list[tuple[str, float]],
    boosts: list[KitBoost],
    debuffs: list[KitDebuff],
    element: str | None,
) -> list[str]:
    """Readable list of team buffs/debuffs that actually affect this member."""
    elem_key = ELEMENT_DMG_KEY.get(element) if element else None
    elem_keys = set(ELEMENT_DMG_KEY.values())
    out: list[str] = []
    seen: set[str] = set()

    def add(label: str) -> None:
        if label not in seen:
            seen.add(label)
            out.append(label)

    for key, val in team_buffs:
        if not val or (key in elem_keys and key != elem_key):
            continue  # off-element damage buffs don't help this member
        add(f"{stat_label(key)} +{val:g}%")
    for b in boosts:
        if b.value and b.element in (None, element):
            add(f"{boost_label(b.element, b.skill_type)} +{b.value:g}%")
    for d in debuffs:
        if d.value and d.element in (None, element):
            add(f"{debuff_label(d.sub, d.element)} {d.value:g}%")
    return out


# --- real-account snapshot → absolute damage (subproject D) ------------------
class SnapshotDamageRequest(BaseModel):
    snapshot: CharacterSnapshot  # from the vision OCR /vision/extract result
    opts: OptsIn = Field(default_factory=OptsIn)
    skill_levels: dict[int, int] = Field(default_factory=dict)
    full_uptime: bool = False


class SnapshotDamageResponse(BaseModel):
    reso_id: str
    name: str | None = None
    element: str | None = None
    set_name: str | None = None
    stats: dict[str, float]
    skills: list[SkillOut]
    total: float
    cost: int
    unresolved: list[str] = Field(default_factory=list)  # OCR labels not mapped


def snapshot_damage_api(
    req: SnapshotDamageRequest, data: EngineData | None = None
) -> SnapshotDamageResponse:
    """Absolute damage for the player's real build. ``data`` defaults to the cached engine."""
    result = snapshot_damage(
        data or get_engine(),
        req.snapshot,
        opts=_damage_opts(req.opts),
        skill_levels=req.skill_levels or None,
        full_uptime=req.full_uptime,
    )
    return SnapshotDamageResponse(
        reso_id=result["reso_id"],
        name=result["name"],
        element=result["element"],
        set_name=result["set_name"],
        stats={k: round(v, 2) for k, v in result["stats"].items()},
        skills=[SkillOut(**s) for s in result["skills"]],
        total=result["total"],
        cost=result["cost"],
        unresolved=result["unresolved"],
    )
