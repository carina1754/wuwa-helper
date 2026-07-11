"""이름 혼동(치사/치샤) 방어 회귀 테스트.

로컬 소형 LLM이 한 음절만 다른 공명자 이름을 헷갈리는 문제를, 결정적 이름 리졸버 +
후검증으로 잡는다. 실제 카탈로그(파일 정본)를 사용해 치사(1508)/치샤(1202)를 검증한다.
"""
from __future__ import annotations

from src.ai_coach import (
    _confusable_siblings,
    _enforce_mentioned_resonators,
    _enforce_pinned_main_dps,
    _fetch_catalog,
    _resolve_mentioned_resonators,
    _resolve_pinned_main_dps,
)
from src.models import AiChatResponse, Recommendation, TeamPick


def _id_by_name(catalog, name):
    for rid, r in catalog["resonators"].items():
        if r.get("name_ko") == name:
            return rid
    raise AssertionError(f"공명자 없음: {name}")


def test_chisa_vs_chixia_resolve_distinctly():
    cat = _fetch_catalog()
    chisa = _id_by_name(cat, "치사")
    chixia = _id_by_name(cat, "치샤")
    assert chisa != chixia
    assert _resolve_mentioned_resonators("치사랑 붙여주는 빌드로 다시 짜줘", cat) == [chisa]
    assert _resolve_mentioned_resonators("치샤 고점팀 짜줘", cat) == [chixia]


def test_confusable_map_links_chisa_chixia():
    cat = _fetch_catalog()
    chisa = _id_by_name(cat, "치사")
    chixia = _id_by_name(cat, "치샤")
    sib = _confusable_siblings(cat)
    assert chixia in sib.get(chisa, set())
    assert chisa in sib.get(chixia, set())


def test_enforce_swaps_confusable_sibling():
    cat = _fetch_catalog()
    chisa = _id_by_name(cat, "치사")
    chixia = _id_by_name(cat, "치샤")
    # 사용자는 치사를 명시했는데 팀엔 치샤가 잘못 들어간 상황
    resp = AiChatResponse(
        reply="추천이에요",
        is_final=True,
        recommendation=Recommendation(
            summary="s", team=[TeamPick(resonator_id=chixia, role="main_dps")]
        ),
    )
    out = _enforce_mentioned_resonators(resp, [chisa], cat)
    assert [p.resonator_id for p in out.recommendation.team] == [chisa]
    assert "자동 교정" in out.reply


def test_enforce_noop_when_already_correct():
    cat = _fetch_catalog()
    chisa = _id_by_name(cat, "치사")
    resp = AiChatResponse(
        reply="ok",
        is_final=True,
        recommendation=Recommendation(
            summary="s", team=[TeamPick(resonator_id=chisa, role="main_dps")]
        ),
    )
    out = _enforce_mentioned_resonators(resp, [chisa], cat)
    assert [p.resonator_id for p in out.recommendation.team] == [chisa]
    assert "자동 교정" not in out.reply


def test_resolve_pinned_main_dps():
    cat = _fetch_catalog()
    phoebe = _id_by_name(cat, "페비")
    assert _resolve_pinned_main_dps("메인딜 지정: 페비", cat) == phoebe
    assert _resolve_pinned_main_dps("페비 메인딜로 짜줘", cat) == phoebe
    assert _resolve_pinned_main_dps("페비랑 치사 조합 짜줘", cat) is None  # 핀 키워드 없음


def test_enforce_pinned_forces_main_dps_role():
    cat = _fetch_catalog()
    phoebe = _id_by_name(cat, "페비")  # 기본 role=support
    rover = _id_by_name(cat, "방랑자 · 회절")  # 기본 role=main_dps
    resp = AiChatResponse(
        reply="추천",
        is_final=True,
        recommendation=Recommendation(
            summary="s",
            team=[
                TeamPick(resonator_id=rover, role="main_dps"),
                TeamPick(resonator_id=phoebe, role="support"),
            ],
        ),
    )
    out = _enforce_pinned_main_dps(resp, phoebe, cat)
    roles = {p.resonator_id: p.role for p in out.recommendation.team}
    assert roles[phoebe] == "main_dps"
    assert roles[rover] == "sub_dps"  # 기존 main_dps는 강등
    assert "메인 딜러로 맞췄어요" in out.reply
