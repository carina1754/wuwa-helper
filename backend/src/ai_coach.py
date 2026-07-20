from __future__ import annotations

import json
import os
import unicodedata

from openai import OpenAI

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
- 역할: main_dps(주 딜러)·sub_dps(보조 딜러)·support(버퍼/디버퍼)·healer(힐러).
- 파티는 **정확히 3명**(게임 규칙상 4명 이상 불가). 주딜1+보조/서폿1+힐/서폿1 구성을 기본으로 한다.
- 사용자가 보유(owned_characters)로 지정한 공명자를 우선 사용하고, 임의로 다른 캐릭터로 대체하지 않는다.
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
- team 배열은 **최대 3개**(게임 파티 정원 3명). 4명 이상 절대 금지.
- 모든 id는 반드시 아래 카탈로그 인덱스에 존재하는 값만 사용한다(환각 금지).
- echo.sub_stats에는 추천 추가옵션(추옵)을 우선순위 순 한국어 스탯명으로 최대 5개까지 넣는다(id 금지).
- upgrade_order의 각 문자열은 한국어 이름만 쓰고 id·괄호숫자를 넣지 않는다(예: "루시 무기 → 에코").
- 정보가 부족하면 recommendation을 null로 두고 reply에서 추가 질문을 한다.
- 사용자가 확정을 원하거나 충분한 정보가 모였을 때만 recommendation을 채우고, 최종안이면 is_final=true.
"""


def _fetch_catalog() -> dict[str, dict[str, dict]]:
    """카탈로그 원본을 id→행 dict로 반환(필터/검증 공용). 파일 정본(data/catalog)에서 로드.

    필드/정렬은 기존 SQL(ORDER BY, cost=4·rarity>=3 필터)과 동치로 유지한다. 무기의
    weapon_type은 옛 컬럼과 동일하게 blob의 weapon_type_ko(한글)를 쓴다.
    """
    from .catalog import (
        load_codex_echoes,
        load_codex_resonators,
        load_codex_weapons,
        load_sonata_sets,
    )

    def _int(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    resonators: dict[str, dict] = {}
    for r in sorted(load_codex_resonators(), key=lambda x: (-_int(x.get("rarity")), _int(x.get("id")))):
        resonators[str(r["id"])] = {
            "id": str(r["id"]),
            "name_ko": r.get("name"),
            "element": r.get("element"),
            "weapon_type": r.get("weapon_type"),
            "rarity": _int(r.get("rarity")),
            "role": r.get("role"),
        }
    weapons: dict[str, dict] = {}
    for w in sorted(
        (x for x in load_codex_weapons() if _int(x.get("rarity")) >= 3),
        key=lambda x: (-_int(x.get("rarity")), str(x.get("id"))),
    ):
        weapons[str(w["id"])] = {
            "id": str(w["id"]),
            "name_ko": w.get("name_ko"),
            "weapon_type": w.get("weapon_type_ko") or w.get("weapon_type"),
            "rarity": _int(w.get("rarity")),
        }
    echoes: dict[str, dict] = {}
    for e in sorted((x for x in load_codex_echoes() if _int(x.get("cost")) == 4), key=lambda x: str(x.get("id"))):
        echoes[str(e["id"])] = {
            "id": str(e["id"]),
            "name_ko": e.get("name_ko"),
            "cost": _int(e.get("cost")),
            "rarity": _int(e.get("rarity")),
        }
    sonatas: dict[str, dict] = {}
    for s in sorted(load_sonata_sets(), key=lambda x: str(x.get("id"))):
        sonatas[str(s["id"])] = {
            "id": str(s["id"]),
            "name_ko": s.get("name_ko"),
            "two_piece": s.get("two_piece"),
            "five_piece": s.get("five_piece"),
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


# --- 이름 혼동 방지: 자유 텍스트 챗에서 명시한 공명자를 결정적으로 해석 ------------
# 로컬 소형 LLM은 "치사"와 "치샤"처럼 한 음절만 다른 이름을 헷갈려 엉뚱한 id를 고르곤 한다.
# 드롭다운(구조적 id 선택)은 멀쩡하므로, 챗에서도 이름→id를 코드로 확정해 같은 신뢰도를 준다.

def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def _resonator_name_pairs(catalog: dict[str, dict[str, dict]]) -> list[tuple[str, str]]:
    """(name, id) 목록 — 정확 매칭용. 전체 이름 + 고유한 '·' 분절 별칭.

    사용자는 '양양·현령'을 '현령'처럼 줄여 부르므로, 로스터 전체에서 정확히 한 공명자에만
    등장하고 다른 정식명과 겹치지 않는 분절만 별칭으로 추가한다(모호하면 제외 → 오검출 방지).
    """
    full: list[tuple[str, str]] = []
    for r in catalog["resonators"].values():
        nm = r.get("name_ko")
        if nm:
            full.append((_nfc(str(nm)), str(r["id"])))
    pairs = list(full)
    full_names = {nm for nm, _ in full}
    seg_owners: dict[str, set[str]] = {}
    for nm, rid in full:
        for sep in ("·", "・", "："):
            if sep in nm:
                for seg in nm.split(sep):
                    seg = seg.strip()
                    if len(seg) >= 2:
                        seg_owners.setdefault(seg, set()).add(rid)
    for seg, owners in seg_owners.items():
        if len(owners) == 1 and seg not in full_names:
            pairs.append((seg, next(iter(owners))))
    return pairs


def _resolve_mentioned_resonators(text: str, catalog: dict[str, dict[str, dict]]) -> list[str]:
    """자유 텍스트에서 정확 부분문자열로 언급된 공명자 id를 추출.

    긴 이름부터 매칭·마스킹해 짧은 이름이 긴 이름 안에서 오검출되지 않게 한다
    (예: '양양·현령'을 먼저 잡고 그 안의 '양양'이 다시 잡히지 않게). '치사'는 '치샤'의
    부분문자열이 아니므로 정확 매칭만으로 둘이 깔끔히 구분된다 — 이게 이 버그의 핵심.
    """
    masked = _nfc(text)
    if not masked:
        return []
    found: list[str] = []
    for name, rid in sorted(_resonator_name_pairs(catalog), key=lambda x: -len(x[0])):
        if name and name in masked:
            found.append(rid)
            masked = masked.replace(name, " " * len(name))
    seen: set[str] = set()
    out: list[str] = []
    for rid in found:
        if rid not in seen:
            seen.add(rid)
            out.append(rid)
    return out


def _confusable_siblings(catalog: dict[str, dict[str, dict]]) -> dict[str, set[str]]:
    """이름이 정확히 한 음절만 다른 공명자 쌍 → id→{유사 id} (예: 치사↔치샤)."""
    ros = [(_nfc(str(r.get("name_ko") or "")), str(r["id"])) for r in catalog["resonators"].values()]
    sib: dict[str, set[str]] = {}
    for na, ia in ros:
        for nb, ib in ros:
            if ia == ib or not na or not nb or len(na) != len(nb):
                continue
            if sum(1 for x, y in zip(na, nb) if x != y) == 1:
                sib.setdefault(ia, set()).add(ib)
    return sib


def _mentioned_constraint_block(mentioned: list[str], catalog: dict[str, dict[str, dict]]) -> str:
    ros = catalog["resonators"]
    sib = _confusable_siblings(catalog)
    lines = [
        "[중요 · 사용자가 이번 메시지에서 명시한 공명자]",
        "아래 공명자는 사용자가 정확히 지정한 것이다. 반드시 이 id를 그대로 팀에 사용하고,",
        "이름이 비슷한 다른 공명자로 절대 대체하지 마라.",
    ]
    for rid in mentioned:
        nm = ros.get(rid, {}).get("name_ko", rid)
        sibs = sib.get(rid)
        if sibs:
            sib_txt = ", ".join(f"{ros.get(s, {}).get('name_ko', s)}(id {s})" for s in sorted(sibs))
            lines.append(f"- {nm} (id {rid}) — 유사 이름 {sib_txt} 와(과) 혼동 금지")
        else:
            lines.append(f"- {nm} (id {rid})")
    return "\n".join(lines)


def _enforce_mentioned_resonators(
    resp: AiChatResponse, mentioned: list[str], catalog: dict[str, dict[str, dict]]
) -> AiChatResponse:
    """후검증(A): 사용자가 명시한 공명자가 팀에서 빠지고 대신 '유사 이름' 공명자가 들어갔으면
    그 픽의 id를 명시 id로 교정한다(예: 치샤→치사). 유사 이름 충돌일 때만 손대므로 안전하다."""
    rec = resp.recommendation
    if rec is None:
        return resp
    sib = _confusable_siblings(catalog)
    ros = catalog["resonators"]
    team_ids = [p.resonator_id for p in rec.team]
    corrections: list[tuple[str, str]] = []
    for m in mentioned:
        if m in team_ids:
            continue
        for pick in rec.team:
            if pick.resonator_id in sib.get(m, set()):
                old = pick.resonator_id
                pick.resonator_id = m
                note = (
                    f"[자동 교정: 이름이 비슷한 {ros.get(old, {}).get('name_ko', old)}(으)로 잘못 지정되어 "
                    f"사용자가 명시한 {ros.get(m, {}).get('name_ko', m)}(으)로 바꿨습니다] "
                )
                pick.reason = note + (pick.reason or "")
                corrections.append((old, m))
                team_ids = [m if x == old else x for x in team_ids]
                break
    if corrections:
        def _nm(i: str) -> str:
            return ros.get(i, {}).get("name_ko", i)

        detail = " / ".join(f"{_nm(o)}→{_nm(n)}" for o, n in corrections)
        resp.reply = (resp.reply or "") + (
            f"\n\n(참고: 이름이 비슷한 공명자를 자동 교정했어요 — {detail}. "
            "빌드 세부는 지정하신 공명자 기준으로 다시 확인해 주세요.)"
        )
    return resp


# --- 역할 지정: 사용자가 '메인 딜러'로 쓸 공명자를 직접 지정 -------------------------
# 고정 role 태그(예: 페비=support)를 무시하고 사용자의 의도를 우선한다. UI는 메시지에
# "메인딜 지정: <이름>" 마커를 넣고, 자유 텍스트는 "<이름> 메인딜/캐리" 패턴을 가볍게 감지한다.
_PIN_MARKER = "메인딜 지정"
_PIN_KEYWORDS = ("메인딜", "메인 딜", "메인딜러", "메인 딜러", "메인 캐리", "메인으로", "캐리로", "main dps")


def _resolve_pinned_main_dps(text: str, catalog: dict[str, dict[str, dict]]) -> str | None:
    t = _nfc(text)
    if not t:
        return None
    pairs = sorted(_resonator_name_pairs(catalog), key=lambda x: -len(x[0]))
    # 1) 명시 마커 "메인딜 지정: <이름>"
    if _PIN_MARKER in t:
        after = t.split(_PIN_MARKER, 1)[1]
        for name, rid in pairs:
            if name and name in after:
                return rid
    # 2) 자유 텍스트: 핀 키워드가 있으면 키워드 직전에 등장한 공명자를 채택
    low = t.lower()
    kw_pos = min((low.find(k) for k in _PIN_KEYWORDS if k in low), default=-1)
    if kw_pos < 0:
        return None
    positions = [(t.find(name), rid) for name, rid in pairs if name and name in t]
    positions = [(p, rid) for p, rid in positions if p != -1]
    if not positions:
        return None
    before = [(p, rid) for p, rid in positions if p <= kw_pos]
    if before:
        return max(before, key=lambda x: x[0])[1]
    return min(positions, key=lambda x: x[0])[1]


def _pinned_constraint_block(pinned: str, catalog: dict[str, dict[str, dict]]) -> str:
    r = catalog["resonators"].get(pinned, {})
    nm = r.get("name_ko", pinned)
    base_role = r.get("role")
    return (
        "[중요 · 사용자가 지정한 메인 딜러]\n"
        f"사용자는 이 파티의 메인 딜러(main_dps)로 {nm}(id {pinned})를 지정했다. "
        f"{nm}의 기본 역할 태그가 '{base_role}'이더라도 이 파티에서는 반드시 {nm}를 main_dps로 배치하고 "
        "그에 맞는 무기·에코·추옵으로 빌드하라. 다른 공명자를 메인 딜러로 세우지 마라."
    )


def _enforce_pinned_main_dps(
    resp: AiChatResponse, pinned: str, catalog: dict[str, dict[str, dict]]
) -> AiChatResponse:
    """후검증: 지정된 공명자가 팀에 있으면 role=main_dps로 강제하고, 다른 main_dps는 sub_dps로 강등."""
    rec = resp.recommendation
    if rec is None or not pinned:
        return resp
    nm = catalog["resonators"].get(pinned, {}).get("name_ko", pinned)
    team_ids = [p.resonator_id for p in rec.team]
    if pinned not in team_ids:
        return resp
    changed = False
    for pick in rec.team:
        if pick.resonator_id == pinned and pick.role != "main_dps":
            pick.role = "main_dps"
            changed = True
        elif pick.resonator_id != pinned and pick.role == "main_dps":
            pick.role = "sub_dps"
            changed = True
    if changed:
        resp.reply = (resp.reply or "") + f"\n\n(참고: 지정하신 {nm}를 메인 딜러로 맞췄어요.)"
    return resp


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"


def list_models(api_key: str, base_url: str | None = None) -> list[str]:
    """BYO 키로 NVIDIA(OpenAI 호환) 모델 목록 조회. 채팅 불가 계열은 제외."""
    client = OpenAI(base_url=base_url or NVIDIA_BASE_URL, api_key=api_key)
    ids = [m.id for m in client.models.list().data]
    bad = ("embed", "rerank", "safety", "guard", "nemoretriever", "content-safety")
    return sorted(i for i in ids if not any(b in i.lower() for b in bad))


def chat(
    request: AiChatRequest,
    *,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> AiChatResponse:
    # BYO 키: 요청(헤더) > env 순. 키 없으면 목업으로 안내(설정 탭에서 NVIDIA 키 등록).
    key = api_key or os.getenv("LLM_API_KEY")
    if not key:
        return _mock_chat(request)
    base = base_url or os.getenv("LLM_BASE_URL") or NVIDIA_BASE_URL
    chosen_model = model or os.getenv("LLM_MODEL") or DEFAULT_MODEL

    catalog = _fetch_catalog()
    index = build_catalog_index(catalog)
    system = build_system_prompt(request.profile, index)

    # 유사 이름(예: 치사/치샤) 혼동 방지 + 역할 지정: 마지막 사용자 메시지를 결정적으로 해석해
    # 프롬프트에 강제 제약으로 주입하고, 응답 후 오선택을 교정한다.
    last_user = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
    mentioned = _resolve_mentioned_resonators(last_user, catalog)
    if mentioned:
        system = system + "\n" + _mentioned_constraint_block(mentioned, catalog)
    pinned = _resolve_pinned_main_dps(last_user, catalog)
    if pinned:
        system = system + "\n" + _pinned_constraint_block(pinned, catalog)

    client = OpenAI(base_url=base, api_key=key)
    messages = [{"role": "system", "content": system}]
    messages += [{"role": m.role, "content": m.content} for m in request.messages]
    response = client.chat.completions.create(
        model=chosen_model,
        temperature=0.4,
        # 추론(reasoning) 모델은 사고 토큰이 completion 한도를 공유 — 기본 한도(≈1k)면
        # 사고만 하다 본문이 빈 채로 잘려 "응답을 이해하지 못했습니다"가 됨. 넉넉히.
        max_tokens=8192,
        response_format={"type": "json_object"},
        messages=messages,
    )
    resp = _parse_reply(response.choices[0].message.content or "", catalog)
    # 후검증(안전망): 유사 이름 오선택 교정 → 지정 메인 딜러 역할 강제 → 파티 정원 3명 클램프.
    if mentioned:
        resp = _enforce_mentioned_resonators(resp, mentioned, catalog)
    if pinned:
        resp = _enforce_pinned_main_dps(resp, pinned, catalog)
    resp = _clamp_party_size(resp, request.profile, catalog)
    return resp


def _clamp_party_size(resp: AiChatResponse, profile: AiProfile, catalog: dict) -> AiChatResponse:
    """게임 파티 정원 3명 강제(LLM 이 4명+ 반환 시 결정적 컷). 보유 지정 공명자 우선 유지."""
    rec = resp.recommendation
    if not rec or len(rec.team) <= 3:
        return resp
    owned = {n.strip() for n in (profile.owned_characters or []) if n and n.strip()}

    def _is_owned(pick) -> bool:
        r = catalog["resonators"].get(pick.resonator_id)
        return bool(r and (r.get("name_ko") or "").strip() in owned)

    kept = [p for p in rec.team if _is_owned(p)] + [p for p in rec.team if not _is_owned(p)]
    rec.team = kept[:3]
    return resp


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
