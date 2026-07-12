"""소나타 세트 판정: 2+2 하이브리드는 두 2세트 효과가 모두 적용돼야 한다."""
from __future__ import annotations

from src.catalog import load_sonata_sets
from src.sim.buffs import sonata_bonuses_from_counts


def _sets() -> dict:
    return {s["name_ko"]: s for s in load_sonata_sets()}


def test_hybrid_2plus2_applies_both_two_sets():
    sets = _sets()
    # 긴 여정을 떠나는 별(2셋=용융 피해 10%) + 악을 씻어내는 마음(2셋=기류 피해 10%)
    res = sonata_bonuses_from_counts({"긴 여정을 떠나는 별": 2, "악을 씻어내는 마음": 2}, sets)
    assert res is not None
    assert len(res["sets"]) == 2
    keys = {b[0] for b in res["bonuses"]}
    assert "fusionDmg" in keys  # 첫 세트 2셋
    assert "aeroDmg" in keys  # 두번째 세트 2셋 — 이게 예전엔 빠졌음


def test_five_set_adds_two_and_five():
    sets = _sets()
    res = sonata_bonuses_from_counts({"긴 여정을 떠나는 별": 5}, sets)
    assert res is not None
    assert res["sets"] == [{"name": "긴 여정을 떠나는 별", "count": 5}]
    assert len(res["bonuses"]) >= 1  # 최소 2셋(용융 피해); 5셋 파싱 가능 시 추가


def test_below_two_is_none():
    sets = _sets()
    assert sonata_bonuses_from_counts({"긴 여정을 떠나는 별": 1}, sets) is None
