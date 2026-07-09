"""Pure damage math — a faithful port of ``frontend/src/lib/build.ts``.

No DB, no IO. Given a resolved ``stats`` dict (all keys present, see
``stats.STAT_KEYS``) plus a :class:`DamageOpts`, these return numbers identical
to the phro.love-style client oracle. The eight multiplicative terms are:

    Damage = Multiplier × FinalATK × Crit × DMGbonus × Boost × RES × DEF
             × Taken × Total  (+ fixed)

Parity with build.ts is asserted by ``tests/test_sim.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

# element (한글) → damage-bonus stat key
ELEMENT_DMG_KEY: dict[str, str] = {
    "응결": "glacioDmg",
    "용융": "fusionDmg",
    "전도": "electroDmg",
    "기류": "aeroDmg",
    "회절": "spectroDmg",
    "인멸": "havocDmg",
}


def skill_type_dmg_key(skill_type: str | None) -> str | None:
    """Map a skill's type label to its damage-bonus stat key (basic/heavy/…).

    변주·반주·협동·에코 등은 표준 보너스 스탯이 없어 ``None``.
    """
    t = skill_type or ""
    if "강공격" in t:
        return "heavyDmg"
    if "일반" in t or "기본" in t:
        return "basicDmg"
    if "공명 스킬" in t or "공명스킬" in t:
        return "skillDmg"
    if "공명 해방" in t or "공명해방" in t:
        return "liberationDmg"
    return None


def crit_multiplier(stats: Mapping[str, float]) -> float:
    """Expected-value crit: 1 + critRate·(critDMG − 1)."""
    return 1 + (stats["crit"] / 100) * (stats["critDmg"] / 100 - 1)


def def_multiplier(
    my_level: float = 90,
    enemy_level: float = 90,
    def_ignore: float = 0,
    def_reduce: float = 0,
) -> float:
    """(800 + 8·myLv) / (800 + 8·myLv + (792 + 8·enemyLv)(1−ignore)(1−reduce))."""
    return (800 + 8 * my_level) / (
        800 + 8 * my_level + (792 + 8 * enemy_level) * (1 - def_ignore) * (1 - def_reduce)
    )


def res_multiplier(enemy_res: float, res_shred: float) -> float:
    """phro.love RES: raw = 1 − (enemyRes − shred); over-penetration counts half."""
    net = enemy_res - res_shred
    raw = 1 - net
    return 1 + (raw - 1) * 0.5 if raw > 1 else raw


@dataclass
class DamageOpts:
    """All adjustable conditions of the formula (defaults = phro.love baseline)."""

    my_level: float = 90
    enemy_level: float = 90
    enemy_res: float = 0.2  # 0.2 = 20%
    res_shred: float = 0  # 저항 무시
    def_ignore: float = 0  # 방어 무시 (0..1)
    def_reduce: float = 0  # 방어 감소 (0..1)
    boost: float = 0  # 부스트 % (독립 항)
    dmg_taken: float = 0  # 받는 피해 %
    total_dmg: float = 0  # 최종 피해 %
    bonus_pct: float = 0  # 추가 피해증가 % (버프)
    fixed_dmg: float = 0  # 고정 추가 피해 (마지막에 가산)


def skill_damage(
    stats: Mapping[str, float],
    multiplier_pct: float,
    element: str | None,
    skill_type: str | None,
    opts: DamageOpts | None = None,
) -> float:
    """One normal-skill hit. ``stats`` must carry every key in ``STAT_KEYS``."""
    o = opts or DamageOpts()
    elem_key = ELEMENT_DMG_KEY.get(element) if element else None
    type_key = skill_type_dmg_key(skill_type)
    dmg_bonus = 1 + (
        (stats[elem_key] if elem_key else 0)
        + (stats[type_key] if type_key else 0)
        + o.bonus_pct
    ) / 100
    res = res_multiplier(o.enemy_res, o.res_shred)
    dfn = def_multiplier(o.my_level, o.enemy_level, o.def_ignore, o.def_reduce)
    base = (
        (multiplier_pct / 100)
        * stats["atk"]
        * crit_multiplier(stats)
        * dmg_bonus
        * (1 + o.boost / 100)
        * res
        * dfn
        * (1 + o.dmg_taken / 100)
        * (1 + o.total_dmg / 100)
    )
    return base + o.fixed_dmg


# --- Anomaly (이상) damage ----------------------------------------------------
# 원소 → 이상 유형 (phro.love 이상 페이지 기준). 캐릭터 속성으로 자동 결정.
ELEMENT_ANOMALY: dict[str, str] = {
    "응결": "서리",
    "용융": "불꽃",
    "전도": "전자",
    "기류": "풍식",
    "회절": "광학",
    "인멸": "암흑",
}


def anomaly_def_reduce(cfg: Mapping, type_: str, stacks: float) -> float:
    """암흑(디버프형) 방어 감소 = 스택 × 2% (최대 6%). 직접 피해는 없음."""
    t = cfg["types"].get(type_)
    if not t or t.get("mode") != "debuff":
        return 0
    return min(t.get("maxDef", 0.06), t.get("defPerStack", 0.02) * max(0, stacks))


def anomaly_base(cfg: Mapping, type_: str, stacks: float, my_level: float = 90) -> float:
    """Anomaly base value B(L) × element coefficient / stack function."""
    base_tbl = cfg["base"]
    b = base_tbl.get(str(my_level)) or base_tbl.get("90") or 3674
    t = cfg["types"].get(type_)
    if not t:
        return 0
    mode = t.get("mode")
    if mode == "burst":
        over = max(0, stacks - t.get("maxStack", 10))
        return b * t.get("coef", 0) * (1 + t.get("overBonus", 0.33) * over)
    if mode == "tick_decay":
        # 3674 × coef × Σ스택, 매 틱 스택 절반(내림)으로 감쇠 (예: 10→5→2→1 = 18)
        s = max(0, int(stacks))
        total = 0
        while s > 0:
            total += s
            s //= 2
        return b * t.get("coef", 0) * total
    if mode == "tick":
        if stacks <= 1:
            return t.get("stack1") if t.get("stack1") is not None else t.get("base", 0) * t.get("stack1Mult", 1)
        return (t.get("perStack") if t.get("perStack") is not None else t.get("base", 0)) * (stacks - 1)
    return 0


def anomaly_damage(
    cfg: Mapping,
    type_: str,
    stacks: float,
    stats: Mapping[str, float],
    opts: DamageOpts | None = None,
    occurrences: float = 1,
) -> float:
    """이상 피해: 방어무시 미적용(방어감소만), 이상치명=1, RES는 스킬과 동일 규칙."""
    o = opts or DamageOpts()
    base_val = anomaly_base(cfg, type_, stacks, o.my_level)
    res = res_multiplier(o.enemy_res, o.res_shred)
    dfn = def_multiplier(o.my_level, o.enemy_level, 0, o.def_reduce)
    return base_val * occurrences * (1 + o.boost / 100) * 1 * dfn * res * (1 + o.total_dmg / 100)


# --- Concerto / Tune break (조화도 파괴) damage --------------------------------
def tune_break_damage(
    multiplier_pct: float,
    opts: DamageOpts | None = None,
    boost_points: float = 0,
    tune_dmg_pct: float = 0,
    crit_rate: float = 0,
    crit_dmg: float = 0,
    repeat: float = 1,
) -> float:
    """10000 × mult × boost × crit × RES × DEF × tuneDmgBonus × repeat."""
    o = opts or DamageOpts()
    boost = (100 + boost_points) / 100
    crit = 1 + (crit_rate / 100) * (crit_dmg / 100 - 1)  # 기대값 (기본 150% ⇒ ×0.5)
    res = res_multiplier(o.enemy_res, o.res_shred)
    dfn = def_multiplier(o.my_level, o.enemy_level, o.def_ignore, o.def_reduce)
    return (
        10000
        * (multiplier_pct / 100)
        * boost
        * crit
        * res
        * dfn
        * (1 + tune_dmg_pct / 100)
        * repeat
    )
