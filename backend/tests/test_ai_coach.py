from __future__ import annotations

from src import ai_coach
from src.models import AiChatRequest, AiMessage, AiProfile


def test_mock_chat_when_no_llm(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    req = AiChatRequest(
        messages=[AiMessage(role="user", content="딜러 추천")],
        profile=AiProfile(union_level=40),
    )
    resp = ai_coach.chat(req)
    assert resp.recommendation is None
    assert resp.is_final is False
    assert "목업" in resp.reply


def test_catalog_index_contains_ids_and_names():
    index = ai_coach.build_catalog_index()
    # 공명자/무기/에코/소나타 섹션 헤더 존재
    assert "공명자" in index
    assert "무기" in index
    assert "에코" in index
    assert "소나타" in index
    # 실데이터 샘플: 양양(1402) 포함
    assert "1402" in index and "양양" in index


def test_system_prompt_embeds_profile_and_contract():
    profile = AiProfile(union_level=55, desired_characters=["창리"], play_style="딜")
    prompt = ai_coach.build_system_prompt(profile, catalog_index="[IDX]")
    assert "55" in prompt
    assert "창리" in prompt
    assert "출력 계약" in prompt
    assert "[IDX]" in prompt


def test_parse_reply_filters_unknown_ids():
    catalog = ai_coach._fetch_catalog()
    known_res = next(iter(catalog["resonators"]))
    raw = (
        '{"reply":"추천합니다","is_final":true,"recommendation":{'
        '"summary":"테스트","team":['
        '{"resonator_id":"' + known_res + '","role":"main_dps",'
        '"weapon":{"id":"99999999","alt_ids":[]},'
        '"echo":{"sonata_ids":["bad-sonata"],"main_echo_id":"00000000"}},'
        '{"resonator_id":"00000000","role":"support"}'
        '],"upgrade_order":["무기 강화"]}}'
    )
    resp = ai_coach._parse_reply(raw, catalog)
    assert resp.is_final is True
    assert resp.recommendation is not None
    team = resp.recommendation.team
    # 알 수 없는 공명자(00000000)는 팀에서 제거, 유효 공명자만 남음
    assert len(team) == 1
    assert team[0].resonator_id == known_res
    # 알 수 없는 무기/에코/소나타는 제거됨
    assert team[0].weapon is None
    assert team[0].echo.main_echo_id is None
    assert team[0].echo.sonata_ids == []


def test_parse_reply_hides_non_json_output():
    # JSON 강제 모드에서 비JSON = 잘림/추론 누출 — 원문 대신 한국어 재시도 안내
    catalog = {"resonators": {}, "weapons": {}, "echoes": {}, "sonatas": {}}
    resp = ai_coach._parse_reply('We need to respond with JSON only. The user says "', catalog)
    assert resp.recommendation is None
    assert "We need" not in resp.reply
    assert "잘렸" in resp.reply
