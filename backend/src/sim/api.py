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
from .formula import DamageOpts
from .loader import EngineData, character_damages, load_engine_data
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
    team_buffs = [(b.key, b.value) for b in req.team_buffs]
    members_out: list[MemberOut] = []
    team_total = 0.0
    for m in req.members:
        reso = data.resonators_by_id.get(str(m.reso_id))
        if reso is None:
            raise KeyError(f"unknown resonator id: {m.reso_id}")
        opts = replace(_damage_opts(base, req.party_def_shred), my_level=m.level)
        build = ResonatorBuild(
            level=m.level, weapon_id=m.weapon_id, weapon_level=m.weapon_level,
            weapon_rank=m.weapon_rank, echoes=_echoes(m.echoes),
        )
        res = character_damages(
            data, m.reso_id, build, opts=opts,
            skill_levels=m.skill_levels, extra_add=team_buffs or None,
            full_uptime=m.full_uptime,
        )
        total = sum(s["dmg"] for s in res["skills"])
        team_total += total
        members_out.append(
            MemberOut(
                reso_id=str(m.reso_id),
                name=reso.get("name") or reso.get("nickname"),
                element=reso.get("element"),
                stats={k: round(v, 2) for k, v in res["stats"].items()},
                skills=[SkillOut(**s) for s in res["skills"]],
                total=total,
                cost=build_cost(build),
            )
        )
    return TeamCalcResponse(members=members_out, team_total=team_total)


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
