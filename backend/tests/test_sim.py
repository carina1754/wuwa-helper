"""Fixed-vector parity tests for the damage engine (src/sim).

Expected values are composed from raw arithmetic (literal rationals like
1520/3032 for DEF@90), independent of the functions under test, so these check
the port's *composition* — not f == f. Numbers mirror frontend/src/lib/build.ts.
"""

from __future__ import annotations

import pytest

from src.sim.formula import (
    DamageOpts,
    ELEMENT_DMG_KEY,
    anomaly_base,
    anomaly_damage,
    anomaly_def_reduce,
    crit_multiplier,
    def_multiplier,
    res_multiplier,
    skill_damage,
    skill_type_dmg_key,
    tune_break_damage,
)
from src.sim.buffs import (
    active_set_bonuses,
    parse_set_effect,
    weapon_buffs,
    weapon_desc_at_rank,
)
from src.sim.loader import (
    EngineData,
    character_damages,
    member_extra_damages,
    rate_at,
    resolve_buffs,
    to_game_config,
)
from src.sim.stats import (
    EchoBuild,
    EchoMainOpt,
    GameConfig,
    ResonatorBuild,
    compute_stats,
    echo_main_value,
    empty_stats,
)

DEF90 = 1520 / 3032  # (800+720)/(800+720+(792+720))


def _stats(**overrides: float) -> dict[str, float]:
    s = empty_stats()
    s.update(overrides)
    return s


# --- primitives --------------------------------------------------------------
def test_def_multiplier() -> None:
    assert def_multiplier(90, 90, 0, 0) == pytest.approx(DEF90)
    # ignore and reduce enter identically as (1 - x)
    assert def_multiplier(90, 90, 0.5, 0) == pytest.approx(1520 / (1520 + 1512 * 0.5))
    assert def_multiplier(90, 90, 0, 0.5) == pytest.approx(1520 / (1520 + 1512 * 0.5))


def test_res_multiplier() -> None:
    assert res_multiplier(0.2, 0) == pytest.approx(0.8)
    assert res_multiplier(0.4, 0) == pytest.approx(0.6)
    assert res_multiplier(0.0, 0) == pytest.approx(1.0)
    # over-penetration (raw > 1) counts half
    assert res_multiplier(0.2, 0.5) == pytest.approx(1 + 0.3 * 0.5)


def test_crit_multiplier() -> None:
    assert crit_multiplier(_stats(crit=50, critDmg=200)) == pytest.approx(1.5)
    assert crit_multiplier(_stats(crit=100, critDmg=250)) == pytest.approx(2.5)
    assert crit_multiplier(_stats(crit=0, critDmg=150)) == pytest.approx(1.0)


def test_skill_type_and_element_keys() -> None:
    assert skill_type_dmg_key("공명 스킬") == "skillDmg"
    assert skill_type_dmg_key("일반 공격") == "basicDmg"
    assert skill_type_dmg_key("강공격") == "heavyDmg"
    assert skill_type_dmg_key("공명 해방") == "liberationDmg"
    assert skill_type_dmg_key("변주") is None
    assert ELEMENT_DMG_KEY["용융"] == "fusionDmg"


# --- skill damage (8-term composition) --------------------------------------
def test_skill_damage_full_composition() -> None:
    stats = _stats(atk=2000, crit=50, critDmg=200, fusionDmg=50)
    got = skill_damage(stats, 100, "용융", "공명 스킬", DamageOpts())
    # mult=1 · atk · crit(1.5) · dmgBonus(1+50/100) · boost(1) · res(0.8) · def · taken(1) · total(1)
    expected = 1.0 * 2000 * 1.5 * 1.5 * 1.0 * 0.8 * DEF90 * 1.0 * 1.0
    assert got == pytest.approx(expected)


def test_skill_damage_type_bonus_and_fixed() -> None:
    stats = _stats(atk=1000, crit=0, critDmg=150, basicDmg=20)
    got = skill_damage(stats, 50, None, "일반 공격", DamageOpts(fixed_dmg=100))
    # crit=1, elem none, typeKey basicDmg=20 → dmgBonus 1.2
    expected = (50 / 100) * 1000 * 1.0 * 1.2 * 1.0 * 0.8 * DEF90 + 100
    assert got == pytest.approx(expected)


def test_skill_damage_no_type_no_element() -> None:
    stats = _stats(atk=1000, crit=0, critDmg=150, basicDmg=99)
    got = skill_damage(stats, 100, None, "변주", DamageOpts(bonus_pct=10))
    # 변주 has no type key → basicDmg ignored; only bonus_pct feeds dmgBonus
    expected = 1.0 * 1000 * 1.0 * (1 + 10 / 100) * 1.0 * 0.8 * DEF90
    assert got == pytest.approx(expected)


# --- anomaly -----------------------------------------------------------------
ANOM_CFG = {
    "base": {"90": 3674},
    "types": {
        "불꽃": {"mode": "burst", "coef": 1.0, "maxStack": 10, "overBonus": 0.33},
        "서리": {"mode": "tick_decay", "coef": 1.0},
        "전자": {"mode": "tick", "base": 100, "stack1Mult": 2, "perStack": 50},
        "암흑": {"mode": "debuff", "defPerStack": 0.02, "maxDef": 0.06},
    },
}


def test_anomaly_base_modes() -> None:
    assert anomaly_base(ANOM_CFG, "불꽃", 10) == pytest.approx(3674)  # at cap, no over
    assert anomaly_base(ANOM_CFG, "불꽃", 12) == pytest.approx(3674 * (1 + 0.33 * 2))
    assert anomaly_base(ANOM_CFG, "서리", 10) == pytest.approx(3674 * (10 + 5 + 2 + 1))
    assert anomaly_base(ANOM_CFG, "전자", 1) == pytest.approx(100 * 2)  # stack1: base×mult
    assert anomaly_base(ANOM_CFG, "전자", 3) == pytest.approx(50 * (3 - 1))  # perStack
    assert anomaly_base(ANOM_CFG, "미지", 5) == 0


def test_anomaly_def_reduce() -> None:
    assert anomaly_def_reduce(ANOM_CFG, "암흑", 2) == pytest.approx(0.04)
    assert anomaly_def_reduce(ANOM_CFG, "암흑", 5) == pytest.approx(0.06)  # capped
    assert anomaly_def_reduce(ANOM_CFG, "불꽃", 5) == 0  # not a debuff


def test_anomaly_damage() -> None:
    got = anomaly_damage(ANOM_CFG, "불꽃", 10, empty_stats(), DamageOpts())
    expected = 3674 * 1 * 1 * 1 * DEF90 * 0.8 * 1
    assert got == pytest.approx(expected)


# --- tune break --------------------------------------------------------------
def test_tune_break_damage() -> None:
    assert tune_break_damage(100) == pytest.approx(10000 * 1 * 1 * 0.8 * DEF90)
    got = tune_break_damage(
        100, boost_points=50, tune_dmg_pct=20, crit_rate=100, crit_dmg=200, repeat=2
    )
    expected = 10000 * 1.5 * 2.0 * 0.8 * DEF90 * 1.2 * 2
    assert got == pytest.approx(expected)


# --- compute_stats -----------------------------------------------------------
def test_echo_main_value() -> None:
    assert echo_main_value(30, 25) == pytest.approx(30.0)  # L25 = full max
    assert echo_main_value(30, 0) == pytest.approx(30 * 0.14)  # L0 ≈ 14%


def _reso() -> dict:
    curve = lambda v: [{"level": 90, "value": v}]
    return {
        "stat_curves": {
            "Life": curve(10000),
            "Atk": curve(300),
            "Def": curve(150),
            "Crit": curve(5),
            "CritDamage": curve(150),
        }
    }


def test_compute_stats_weapon_and_extra() -> None:
    weapon = {
        "properties": [
            {"curve": [{"level": 90, "value": 500}]},
            {"name": "공격력", "curve": [{"level": 90, "value": 36}]},
        ]
    }
    build = ResonatorBuild(level=90, weapon_level=90)
    out = compute_stats(_reso(), weapon, build, None, extra=[("atkPct", 10), ("crit", 20), ("fusionDmg", 30)])
    # atkPct = 36 (weapon sub) + 10 (extra) folds into final atk = (300 + 500) × 1.46
    assert out["atk"] == pytest.approx(1168.0)
    assert out["atkPct"] == pytest.approx(0.0)  # %-stats consumed into atk, not surfaced (as in build.ts)
    assert out["crit"] == pytest.approx(25.0)  # base 5 + extra 20
    assert out["critDmg"] == pytest.approx(150.0)
    assert out["fusionDmg"] == pytest.approx(30.0)
    assert out["hp"] == pytest.approx(10000.0)
    assert out["def"] == pytest.approx(150.0)
    assert out["energyRegen"] == pytest.approx(100.0)


def test_compute_stats_echo_main_and_subs() -> None:
    config = GameConfig(cost_budget=12, main={"4": [EchoMainOpt("atkPct", 30)]})
    echo = EchoBuild(echo_id="e1", cost=4, grade=5, level=25, main="atkPct", subs=[("crit", 5)])
    build = ResonatorBuild(level=90, weapon_level=90, echoes=[echo, None, None, None, None])
    out = compute_stats(_reso(), None, build, config)
    # echo main atkPct = echo_main_value(30, 25) = 30 → atk 300 × 1.30 = 390
    assert out["atk"] == pytest.approx(390.0)
    assert out["crit"] == pytest.approx(10.0)  # base 5 + sub 5


# --- loader (DB → engine glue, tested without a DB) --------------------------
def test_rate_at() -> None:
    assert rate_at(["50", "60"], 1) == pytest.approx(50.0)
    assert rate_at(["50", "60"], 10) == pytest.approx(60.0)  # clamped to last
    assert rate_at(["50", "60"], 0) == pytest.approx(50.0)  # clamped to first
    assert rate_at(["12.8%"], 1) == pytest.approx(12.8)  # percent string parsed
    assert rate_at([], 5) == 0.0


def test_to_game_config() -> None:
    cfg = to_game_config(
        {
            "costBudget": 10,
            "main": {"4": [{"key": "atkPct", "max": 30}]},
            "sub": [{"key": "crit", "max": 10}],
            "subSlots": {"5": 5},
        }
    )
    assert cfg.cost_budget == 10
    assert cfg.main["4"][0] == EchoMainOpt("atkPct", 30)
    assert cfg.sub_slots["5"] == 5


def _engine_data() -> EngineData:
    weapon = {
        "properties": [
            {"curve": [{"level": 90, "value": 500}]},
            {"name": "공격력", "curve": [{"level": 90, "value": 36}]},
        ]
    }
    reso = _reso()
    reso["element"] = "용융"
    reso["skills"] = [
        {"SkillName": "평타", "SkillType": "일반 공격",
         "damage": [{"rates": ["50", "60", "70", "80", "90", "100", "110", "120", "130", "140"]}]},
        {"SkillName": "변주기", "SkillType": "변주", "damage": [{"rates": ["10"]}]},
        {"SkillName": "무딜", "SkillType": "공명 스킬", "damage": []},  # filtered (no damage)
    ]
    return EngineData(
        config=to_game_config({"costBudget": 12, "main": {}, "sub": [], "subSlots": {}}),
        anomaly=None,
        resonators_by_id={"r1": reso},
        weapons_by_id={"w1": weapon},
    )


def test_character_damages_defaults_and_filtering() -> None:
    data = _engine_data()
    build = ResonatorBuild(level=90, weapon_level=90, weapon_id="w1")
    result = character_damages(data, "r1", build)
    # skill 2 (no damage) dropped; two remain, all at default Lv.10
    assert [s["name"] for s in result["skills"]] == ["평타", "변주기"]
    assert all(s["level"] == 10 for s in result["skills"])
    # 평타 at Lv.10 uses rate 140; reproduce with the (tested) primitives
    stats = result["stats"]
    from src.sim.formula import skill_damage as _sd  # local ref, avoid top clutter
    assert result["skills"][0]["dmg"] == pytest.approx(_sd(stats, 140, "용융", "일반 공격"))
    assert result["skills"][1]["dmg"] == pytest.approx(_sd(stats, 10, "용융", "변주"))


def test_character_damages_per_skill_level_override() -> None:
    data = _engine_data()
    build = ResonatorBuild(level=90, weapon_level=90, weapon_id="w1")
    result = character_damages(data, "r1", build, skill_levels={0: 1})
    basic = next(s for s in result["skills"] if s["name"] == "평타")
    assert basic["level"] == 1  # override honored
    from src.sim.formula import skill_damage as _sd
    assert basic["dmg"] == pytest.approx(_sd(result["stats"], 50, "용융", "일반 공격"))  # Lv.1 rate = 50


def test_member_extra_damages_burst_debuff_and_none() -> None:
    data = EngineData(
        config=to_game_config({}),
        anomaly=ANOM_CFG,
        tune_break={"base": 10000, "defaultMultiplier": 16.0},
    )
    stats = _stats(crit=50, critDmg=200)
    opts = DamageOpts()
    # default multiplier 16.0 × 100 → 1600; both branches share this tune-break value
    tune = tune_break_damage(1600, opts, crit_rate=50, crit_dmg=200)

    # 용융 → 불꽃 (burst): direct anomaly damage, no DEF-down
    burst = member_extra_damages(data, "용융", stats, opts)
    assert burst["anomaly_type"] == "불꽃"
    assert burst["anomaly_def_down"] == 0
    assert burst["anomaly_dmg"] == pytest.approx(anomaly_damage(ANOM_CFG, "불꽃", 10, stats, opts))
    assert burst["tune_break_dmg"] == pytest.approx(tune)

    # 인멸 → 암흑 (debuff): DEF-down only, no direct hit
    debuff = member_extra_damages(data, "인멸", stats, opts)
    assert debuff["anomaly_type"] == "암흑"
    assert debuff["anomaly_dmg"] == 0
    assert debuff["anomaly_def_down"] == pytest.approx(anomaly_def_reduce(ANOM_CFG, "암흑", 10))

    # unknown element → no anomaly at all; tune break still computed
    none = member_extra_damages(data, "??", stats, opts)
    assert none["anomaly_type"] is None
    assert none["anomaly_dmg"] == 0 and none["anomaly_def_down"] == 0
    assert none["tune_break_dmg"] == pytest.approx(tune)


# --- buff-semantics layer (sim_buff / A2) ------------------------------------
def test_parse_set_effect() -> None:
    assert parse_set_effect("용융 피해가 10% 증가된다") == ("fusionDmg", 10.0)
    assert parse_set_effect("공격력이 12% 증가") == ("atkPct", 12.0)
    assert parse_set_effect("크리티컬 피해가 20% 증가") == ("critDmg", 20.0)
    assert parse_set_effect("크리티컬이 8% 증가") == ("crit", 8.0)  # 피해 없는 크리 → crit
    assert parse_set_effect("아무 의미 없는 문장") is None
    assert parse_set_effect(None) is None


def test_weapon_desc_at_rank() -> None:
    desc = "<color>공격력</color>이 4%/6.2%/8.4%/10.6%/12.8% 증가"
    assert weapon_desc_at_rank(desc, 1) == "공격력이 4% 증가"  # tags stripped, rank-1 slot
    assert weapon_desc_at_rank(desc, 5) == "공격력이 12.8% 증가"
    assert weapon_desc_at_rank(desc, 9) == "공격력이 12.8% 증가"  # clamped to last


WEAPON_DESC = "공격력이 10%/11%/12%/13%/14% 증가된다. 명중 시 용융 피해 보너스가 5% 증가되며 최대 2스택 중첩된다."


def test_weapon_buffs_always_conditional_and_stacks() -> None:
    wb1 = weapon_buffs({"desc": WEAPON_DESC}, 1)
    assert dict(wb1["always"]) == {"atkPct": 10.0}
    # conditional sentence names triggers (명중/시/스택/중첩); 5% × 2 stacks = 10
    assert dict(wb1["conditional"]) == {"fusionDmg": 10.0}
    assert wb1["boost"] == 0.0
    wb5 = weapon_buffs({"desc": WEAPON_DESC}, 5)
    assert dict(wb5["always"]) == {"atkPct": 14.0}  # rank-5 slot
    assert weapon_buffs(None, 1) == {"always": [], "conditional": [], "boost": 0.0}


def test_active_set_bonuses_two_and_five() -> None:
    set_by_name = {
        "용융 세트": {"two_piece": "용융 피해가 10% 증가된다", "five_piece": "공격력이 20% 증가된다"},
    }
    sonata = {"e1": ["용융 세트"], "e2": ["용융 세트"]}
    echo_sonata = lambda eid: sonata.get(eid, [])
    two_echoes = [
        EchoBuild("e1", 4, 5, 25, "atkPct"),
        EchoBuild("e2", 4, 5, 25, "atkPct"),
        None, None, None,
    ]
    active = active_set_bonuses(ResonatorBuild(echoes=two_echoes), echo_sonata, set_by_name)
    assert active is not None
    assert active["name"] == "용융 세트" and active["count"] == 2
    assert active["bonuses"] == [("fusionDmg", 10.0)]  # 2-piece only

    sonata.update({"e3": ["용융 세트"], "e4": ["용융 세트"], "e5": ["용융 세트"]})
    five_echoes = [EchoBuild(f"e{i}", 4, 5, 25, "atkPct") for i in range(1, 6)]
    active5 = active_set_bonuses(ResonatorBuild(echoes=five_echoes), echo_sonata, set_by_name)
    assert active5["count"] == 5
    assert active5["bonuses"] == [("fusionDmg", 10.0), ("atkPct", 20.0)]  # 2- + 5-piece


def test_resolve_buffs_auto_applies_sonata_and_weapon() -> None:
    weapon = {
        "desc": "공격력이 10% 증가된다.",
        "properties": [{"curve": [{"level": 90, "value": 500}]}, {"name": "공격력", "curve": [{"level": 90, "value": 36}]}],
    }
    data = EngineData(
        config=to_game_config({"main": {}}),
        anomaly=None,
        resonators_by_id={"r1": {**_reso(), "element": "용융", "skills": []}},
        weapons_by_id={"w1": weapon},
        echoes_by_id={"e1": {"sonata": ["용융 세트"]}, "e2": {"sonata": ["용융 세트"]}},
        sonata_by_name={"용융 세트": {"two_piece": "용융 피해가 10% 증가된다"}},
    )
    build = ResonatorBuild(
        level=90, weapon_level=90, weapon_id="w1",
        echoes=[EchoBuild("e1", 4, 5, 25, "atkPct"), EchoBuild("e2", 4, 5, 25, "atkPct"), None, None, None],
    )
    extra, boost = resolve_buffs(data, build)
    assert ("fusionDmg", 10.0) in extra  # sonata 2-piece
    assert ("atkPct", 10.0) in extra  # weapon always-on
    assert boost == 0.0


# --- server team-calculate (src/sim/api, tested without a DB) -----------------
def test_team_calculate_aggregates() -> None:
    from src.sim.api import MemberIn, TeamCalcRequest, team_calculate

    data = _engine_data()
    req = TeamCalcRequest(
        members=[MemberIn(reso_id="r1", weapon_id="w1"), MemberIn(reso_id="r1", weapon_id="w1")]
    )
    resp = team_calculate(req, data=data)
    assert len(resp.members) == 2
    for m in resp.members:
        assert m.element == "용융"
        assert m.skills  # 무딜 (no damage) filtered out upstream
        assert m.total == pytest.approx(sum(s.dmg for s in m.skills))
    assert resp.team_total == pytest.approx(sum(m.total for m in resp.members))


def test_team_calculate_party_def_shred_raises_damage() -> None:
    from src.sim.api import MemberIn, TeamCalcRequest, team_calculate

    data = _engine_data()
    members = [MemberIn(reso_id="r1", weapon_id="w1")]
    base = team_calculate(TeamCalcRequest(members=members), data=data)
    shred = team_calculate(
        TeamCalcRequest(members=members, party_def_shred=0.06), data=data
    )
    # −6% party DEF shred folds into def_reduce → larger DEF multiplier → more damage
    assert shred.team_total > base.team_total


def test_team_calculate_shared_team_buffs_raise_damage() -> None:
    from src.sim.api import MemberIn, SubIn, TeamCalcRequest, team_calculate

    data = _engine_data()
    members = [MemberIn(reso_id="r1", weapon_id="w1")]
    base = team_calculate(TeamCalcRequest(members=members), data=data)
    buffed = team_calculate(
        TeamCalcRequest(members=members, team_buffs=[SubIn(key="atkPct", value=20)]),
        data=data,
    )
    # a shared +20% ATK team buff lifts every member's damage
    assert buffed.team_total > base.team_total


def test_team_calculate_unknown_resonator() -> None:
    from src.sim.api import MemberIn, TeamCalcRequest, team_calculate

    with pytest.raises(KeyError):
        team_calculate(
            TeamCalcRequest(members=[MemberIn(reso_id="nope")]), data=_engine_data()
        )


# --- real-account snapshot → absolute damage (subproject D) ------------------
def test_stat_key_from_ko_flat_vs_percent_and_special() -> None:
    from src.sim.snapshot import stat_key_from_ko as k

    assert k("공격력", "150") == "atk"  # flat by value
    assert k("공격력", "9.4%") == "atkPct"  # percent by value
    assert k("공격력%") == "atkPct"  # percent by name suffix
    assert k("생명력", "320") == "hp"
    assert k("생명력", "6.4%") == "hpPct"
    assert k("방어력", "40") == "def"
    assert k("크리티컬", "6.3%") == "crit"
    assert k("크리티컬 피해", "12.6%") == "critDmg"  # critDmg matched before crit
    assert k("공명 효율", "10%") == "energyRegen"
    assert k("응결 피해 보너스", "30%") == "glacioDmg"  # element dmg
    assert k("공명 스킬 피해 보너스", "12%") == "skillDmg"  # skill-type dmg
    assert k("듣도보도못한스탯") is None


def test_parse_stat_value() -> None:
    from src.sim.snapshot import parse_stat_value as p

    assert p("12.6%") == 12.6
    assert p("1,050") == 1050.0
    assert p("150") == 150.0
    assert p(None) is None
    assert p("N/A") is None


def _snap_engine() -> EngineData:
    reso = _reso()
    reso["name"] = "테스트로르"
    reso["element"] = "용융"
    reso["skills"] = [
        {"SkillName": "평타", "SkillType": "일반 공격", "damage": [{"rates": ["100"] * 10}]}
    ]
    weapon = {
        "name": "테스트검",
        "properties": [
            {"curve": [{"level": 90, "value": 500}]},
            {"name": "공격력", "curve": [{"level": 90, "value": 36}]},
        ],
    }
    config = to_game_config(
        {
            "costBudget": 12,
            "main": {"4": [{"key": "critDmg", "max": 44}], "1": [{"key": "hp", "max": 2280}]},
            "sub": [],
            "subSlots": {},
        }
    )
    sonata = {"화락": {"name_ko": "화락", "two_piece": "용융 피해가 10% 증가", "five_piece": ""}}
    return EngineData(
        config=config,
        anomaly=None,
        resonators_by_id={"9001": reso},
        weapons_by_id={"w9": weapon},
        echoes_by_id={},
        sonata_by_name=sonata,
    )


def test_snapshot_damage_uses_real_subs_and_sonata() -> None:
    from src.models import CharacterSnapshot, EchoItem, SubStat, WeaponState
    from src.sim.snapshot import snapshot_damage

    snap = CharacterSnapshot(
        character_name="테스트로르",
        character_level=90,
        weapon=WeaponState(name="테스트검", level=90, rank=1),
        echoes=[
            EchoItem(
                cost=4, level=25, set_name="화락", main_stat="크리티컬 피해",
                sub_stats=[
                    SubStat(name="공격력", value="9.4%"),
                    SubStat(name="크리티컬 피해", value="21%"),
                    SubStat(name="이상한스탯", value="???"),
                ],
            ),
            EchoItem(cost=1, level=25, set_name="화락", main_stat="생명력",
                     sub_stats=[SubStat(name="크리티컬", value="6.3%")]),
        ],
    )
    out = snapshot_damage(_snap_engine(), snap)
    assert out["reso_id"] == "9001"
    assert out["name"] == "테스트로르"
    assert out["element"] == "용융"
    assert out["set_name"] == "화락"  # both echoes share the set → 2-piece active
    assert out["stats"]["critDmg"] > 150  # real critDmg main + sub applied
    assert out["stats"]["crit"] > 5  # real crit sub applied
    assert out["skills"] and out["total"] > 0
    assert any("이상한스탯" in u for u in out["unresolved"])  # bogus sub surfaced


def test_snapshot_damage_unknown_character_raises() -> None:
    from src.models import CharacterSnapshot
    from src.sim.snapshot import snapshot_damage

    with pytest.raises(KeyError):
        snapshot_damage(_snap_engine(), CharacterSnapshot(character_name="없는캐릭"))
