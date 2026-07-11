"""포르테(스킬트리) 고정 스탯 보너스가 카탈로그에 있고 엔진이 적용하는지 검증."""
from __future__ import annotations

import copy

from src.catalog import load_codex_resonators
from src.sim.stats import ResonatorBuild, compute_stats


def _reso(rid: str) -> dict:
    return {str(r["id"]): r for r in load_codex_resonators()}[rid]


def test_every_resonator_has_forte_bonus():
    for r in load_codex_resonators():
        fb = r.get("forte_bonus")
        assert isinstance(fb, dict) and fb, f"{r.get('id')} missing forte_bonus"


def test_forte_adds_atk_pct_and_element_dmg():
    reso = _reso("1502")  # 방랑자·회절: spectroDmg 12 + atkPct 12
    build = ResonatorBuild(level=90)
    with_forte = compute_stats(reso, None, build, None)
    stripped = copy.deepcopy(reso)
    stripped.pop("forte_bonus")
    without = compute_stats(stripped, None, build, None)
    assert round(with_forte["spectroDmg"] - without["spectroDmg"], 3) == 12.0
    # +12% ATK on the (base+weapon) term
    assert abs(with_forte["atk"] - without["atk"] * 1.12) < 0.01


def test_forte_healer_gives_no_atk():
    reso = _reso("1209")  # 모니에(healer): healing 12 + defPct 15.2 → ATK 불변
    build = ResonatorBuild(level=90)
    with_forte = compute_stats(reso, None, build, None)
    stripped = copy.deepcopy(reso)
    stripped.pop("forte_bonus")
    without = compute_stats(stripped, None, build, None)
    assert with_forte["atk"] == without["atk"]
    assert round(with_forte["healing"] - without["healing"], 3) == 12.0
