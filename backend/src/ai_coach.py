from __future__ import annotations

import json
import os

from openai import OpenAI

from .database import get_connection
from .models import (
    AiChatRequest,
    AiChatResponse,
    AiProfile,
    Recommendation,
)
from .parser import extract_json_object

# 빌드/데미지 규칙 요약 — 모델이 추천 근거로 삼는 핵심 상수(스펙 §2 기준).
RULES_SUMMARY = """[빌드/데미지 규칙 요약]
- 크리티컬 기대값: 크리율×2 + 크리피해 ≈ 200(예: 크리율 70 / 크리피해 130) 을 목표로 서브스탯 배분.
- 메인 에코(cost 4)는 속성피해% 또는 역할별 주요 스탯을 메인스탯으로 선택.
- 소나타 세트: 2세트 효과는 조합 가능, 5세트(주 세트)는 캐릭터 역할/속성에 맞춰 1개 선택.
- 역할: main_dps(주 딜러)·sub_dps(보조 딜러)·support(버퍼/디버퍼)·healer(힐러). 팀은 보통 주딜1+보조/서폿1+힐/서폿1.
- 무기는 캐릭터 무기 타입(weapon_type)이 일치해야 장착 가능. 예산 대안(alt_ids)을 함께 제시.
- 에코 추가옵션(추옵): 캐릭터마다 우선순위가 높은 추옵을 한국어 스탯명으로 최대 5개까지 제시(예: 크리 피해·크리율·공격력%·공명 스킬 피해·공격력). 크리 기대값 목표를 우선하되 역할에 맞게 조정.
- 업그레이드 순서: 보유/희망 주딜의 무기·에코 → 서폿 → 힐러 순으로 자원 투자 권장.
"""

OUTPUT_CONTRACT = """[출력 계약]
사용자와 한국어로 대화하되, 매 응답을 아래 JSON 하나로만 반환한다(코드블록/설명 금지):
{
  "reply": "사용자에게 보여줄 산문 답변(한국어)",
  "is_final": false,
  "recommendation": null 또는 {
    "summary": "한 줄 요약",
    "team": [
      {
        "resonator_id": "카탈로그의 공명자 id(정수 문자열)",
        "role": "main_dps|sub_dps|support|healer",
        "reason": "선택 근거",
        "priority": 1,
        "weapon": {"id": "무기 id", "alt_ids": ["대안 무기 id"], "reason": "근거"},
        "echo": {"sonata_ids": ["소나타 id"], "main_echo_id": "cost4 에코 id", "main_stats": {"cost4": "속성피해"}, "sub_stats": ["크리 피해", "크리율", "공격력%", "공명 스킬 피해", "공격력"]}
      }
    ],
    "upgrade_order": ["추천 업그레이드 순서 문자열", "..."]
  }
}
규칙:
- 모든 id는 반드시 아래 카탈로그 인덱스에 존재하는 값만 사용한다(환각 금지).
- echo.sub_stats에는 추천 추가옵션(추옵)을 우선순위 순 한국어 스탯명으로 최대 5개까지 넣는다(id 금지).
- upgrade_order의 각 문자열은 한국어 이름만 쓰고 id·괄호숫자를 넣지 않는다(예: "루시 무기 → 에코").
- 정보가 부족하면 recommendation을 null로 두고 reply에서 추가 질문을 한다.
- 사용자가 확정을 원하거나 충분한 정보가 모였을 때만 recommendation을 채우고, 최종안이면 is_final=true.
"""


def _fetch_catalog() -> dict[str, dict[str, dict]]:
    """카탈로그 원본을 id→행 dict로 반환(필터/검증 공용)."""
    resonators: dict[str, dict] = {}
    weapons: dict[str, dict] = {}
    echoes: dict[str, dict] = {}
    sonatas: dict[str, dict] = {}
    with get_connection() as conn:
        for row in conn.execute(
            "SELECT id, name_ko, element, weapon_type, rarity, role FROM wuwa_resonator ORDER BY rarity DESC, id"
        ).fetchall():
            resonators[str(row["id"])] = dict(row)
        for row in conn.execute(
            "SELECT id, name_ko, weapon_type, rarity FROM wuwa_weapon WHERE rarity >= 3 ORDER BY rarity DESC, id"
        ).fetchall():
            weapons[str(row["id"])] = dict(row)
        for row in conn.execute(
            "SELECT id, name_ko, cost, rarity FROM wuwa_echo WHERE cost = 4 ORDER BY id"
        ).fetchall():
            echoes[str(row["id"])] = dict(row)
        for row in conn.execute("SELECT id, name_ko, data_json FROM sonata_set ORDER BY id").fetchall():
            data = json.loads(row["data_json"])
            sonatas[str(row["id"])] = {
                "id": str(row["id"]),
                "name_ko": row["name_ko"],
                "two_piece": data.get("two_piece"),
                "five_piece": data.get("five_piece"),
            }
    return {"resonators": resonators, "weapons": weapons, "echoes": echoes, "sonatas": sonatas}


def build_catalog_index(catalog: dict[str, dict[str, dict]] | None = None) -> str:
    """도감을 프롬프트용 압축 텍스트로 조립(Phase 0 검증: ~7.8k 토큰)."""
    cat = catalog or _fetch_catalog()
    lines: list[str] = ["[카탈로그 인덱스]"]
    lines.append("## 공명자 (id | 이름 | 속성 | 무기타입 | 성급 | 역할)")
    for r in cat["resonators"].values():
        lines.append(f"{r['id']}|{r['name_ko']}|{r['element']}|{r['weapon_type']}|{r['rarity']}★|{r['role']}")
    lines.append("## 무기 3성↑ (id | 이름 | 무기타입 | 성급)")
    for w in cat["weapons"].values():
        lines.append(f"{w['id']}|{w['name_ko']}|{w['weapon_type']}|{w['rarity']}★")
    lines.append("## 메인 에코 cost4 (id | 이름)")
    for e in cat["echoes"].values():
        lines.append(f"{e['id']}|{e['name_ko']}")
    lines.append("## 소나타 세트 (id | 이름 | 2셋 | 5셋)")
    for s in cat["sonatas"].values():
        lines.append(f"{s['id']}|{s['name_ko']}|{s['two_piece']}|{s['five_piece']}")
    return "\n".join(lines)


def build_system_prompt(profile: AiProfile, catalog_index: str | None = None) -> str:
    index = catalog_index if catalog_index is not None else build_catalog_index()
    profile_line = json.dumps(profile.model_dump(), ensure_ascii=False)
    return (
        "당신은 명조(Wuthering Waves)의 캐릭터 빌드/파티 코치입니다. "
        "아래 카탈로그와 규칙만 근거로, 사용자 프로필에 맞는 캐릭터·무기·에코·업그레이드 순서를 추천합니다.\n\n"
        f"[사용자 프로필]\n{profile_line}\n\n"
        f"{RULES_SUMMARY}\n"
        f"{OUTPUT_CONTRACT}\n"
        f"{index}\n"
    )


def _filter_recommendation(
    rec: Recommendation, catalog: dict[str, dict[str, dict]]
) -> tuple[Recommendation, list[str]]:
    """카탈로그에 없는 id 제거 + 경고 수집(이중 방어)."""
    warnings: list[str] = []
    kept_team = []
    for pick in rec.team:
        if pick.resonator_id not in catalog["resonators"]:
            warnings.append(f"알 수 없는 공명자 id 제거: {pick.resonator_id}")
            continue
        if pick.weapon and pick.weapon.id not in catalog["weapons"]:
            warnings.append(f"알 수 없는 무기 id 제거: {pick.weapon.id}")
            pick.weapon = None
        if pick.weapon:
            pick.weapon.alt_ids = [a for a in pick.weapon.alt_ids if a in catalog["weapons"]]
        if pick.echo:
            if pick.echo.main_echo_id and pick.echo.main_echo_id not in catalog["echoes"]:
                warnings.append(f"알 수 없는 에코 id 제거: {pick.echo.main_echo_id}")
                pick.echo.main_echo_id = None
            pick.echo.sonata_ids = [s for s in pick.echo.sonata_ids if s in catalog["sonatas"]]
            pick.echo.sub_stats = [s for s in pick.echo.sub_stats if s and s.strip()][:5]
        kept_team.append(pick)
    rec.team = kept_team
    return rec, warnings


def _mock_chat(request: AiChatRequest) -> AiChatResponse:
    """LLM_BASE_URL 미설정 시 결정적 목업(테스트/오프라인용)."""
    last = request.messages[-1].content if request.messages else ""
    return AiChatResponse(
        reply=(
            "목업 코치입니다(LLM_BASE_URL 미설정). "
            f"연각 레벨/희망 캐릭터/플레이 스타일을 알려주시면 추천을 만들어 드릴게요. 입력: {last[:60]}"
        ),
        recommendation=None,
        is_final=False,
    )


def chat(request: AiChatRequest) -> AiChatResponse:
    base_url = os.getenv("LLM_BASE_URL")
    if not base_url:
        return _mock_chat(request)

    catalog = _fetch_catalog()
    index = build_catalog_index(catalog)
    system = build_system_prompt(request.profile, index)

    client = OpenAI(base_url=base_url, api_key=os.getenv("LLM_API_KEY", "sk-local"))
    model = os.getenv("LLM_MODEL", "wuwa-vlm")
    messages = [{"role": "system", "content": system}]
    messages += [{"role": m.role, "content": m.content} for m in request.messages]
    # 이 작업은 규칙·카탈로그를 프롬프트에 주입한 구조화 JSON 추출이라 긴 추론(reasoning)의
    # 이득보다 지연이 크다. 기본적으로 reasoning을 꺼서 응답을 빠르게 한다(Qwen3 계열 토글).
    # LLM_ENABLE_REASONING=1 로 다시 켤 수 있다.
    extra_body: dict = {}
    if os.getenv("LLM_ENABLE_REASONING", "0") != "1":
        extra_body["chat_template_kwargs"] = {"enable_thinking": False}
    response = client.chat.completions.create(
        model=model,
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=messages,
        extra_body=extra_body,
    )
    return _parse_reply(response.choices[0].message.content or "", catalog)


def _parse_reply(raw: str, catalog: dict[str, dict[str, dict]]) -> AiChatResponse:
    try:
        data = extract_json_object(raw)
    except json.JSONDecodeError:
        return AiChatResponse(reply=raw.strip() or "응답을 이해하지 못했습니다.", recommendation=None, is_final=False)

    reply = str(data.get("reply", "")).strip()
    is_final = bool(data.get("is_final", False))
    rec_data = data.get("recommendation")
    recommendation = None
    if isinstance(rec_data, dict):
        try:
            rec = Recommendation.model_validate(rec_data)
            rec, warnings = _filter_recommendation(rec, catalog)
            recommendation = rec
            if warnings and reply:
                reply = reply + "\n\n(참고: 카탈로그에 없는 항목 일부를 제외했습니다.)"
        except Exception:
            recommendation = None
    return AiChatResponse(reply=reply or "…", recommendation=recommendation, is_final=is_final)
