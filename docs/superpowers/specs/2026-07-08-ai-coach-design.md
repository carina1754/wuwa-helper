# AI 코치 탭 설계 (Design Spec)

- 날짜: 2026-07-08
- 상태: 승인됨 (브레인스토밍 완료)
- 대상 브랜치: `implement-mvp`

## 1. 목적

기존 "분석(Analyzer)" 탭을 대화형 **AI 코치** 탭으로 전환한다. 사용자가 연각 레벨·보유/원하는 캐릭터·플레이스타일을 입력하면, 로컬 LLM(Qwen3.6, llama-server)이 DB 도감 데이터와 데미지/빌드 규칙을 근거로 **사용할 캐릭터·무기·에코·추천 업그레이드 순서·빌드**를 대화형으로 추천한다. 사용자가 최종 추천을 확정하면 전용 저장소에 기록한다. 추천은 도감(DB)의 캐릭터/무기/에코 아이콘과 함께 렌더한다.

## 2. 확정된 결정

| 결정 | 선택 | 근거 |
|---|---|---|
| 카탈로그 근거 | 전체 인덱스를 시스템 프롬프트에 주입 | 카탈로그가 유한·소규모(공명자 56·무기 118·에코 245·소나타 34). 압축 시 ~4k 토큰(에코는 추천에 쓰이는 3~4코스트 메인만). 검색 인프라 불필요, id 환각 원천 차단. |
| 최종 추천 저장 | 전용 `ai_recommendations` 테이블 신설 | 대화 로그·확정 픽·업그레이드 순서를 깔끔한 스키마로 저장. 기존 `AnalysisSession`은 `extraction`/`diagnoses` 필수라 성격 불일치(가짜 값 회피). |
| 대화 흐름 | 가이드 인트로 → 자유 대화 | 첫 화면에서 구조화 입력(칩/폼)으로 첫 턴을 결정적으로, 이후 자유 대화. 토큰·변동성 감소, "대화형" 유지. |
| 웹 검색 | v1 보류 (v2 후보) | 정답 데이터는 DB+phro.love 포뮬러에 이미 존재. 라이브 검색은 외부 API 의존·노이즈·지연 증가. 메타 정보가 필요하면 DB 큐레이션이 더 안정적. |
| 스크린샷 분석 | AI 인트로에 **선택적** 통합 | 스크린샷 업로드 시 vision으로 보유 캐릭터/현재 빌드 자동 채움(로컬 비전 활용). **단, 스크린샷 없이 수동 입력만으로도 전체 흐름이 동작해야 함.** |

## 3. 아키텍처 & 데이터 흐름

```
[프론트: AI 탭]
 1) 인트로 폼: 연각 레벨 · 보유/원하는 캐릭터(칩) · 플레이스타일(칩) · 자유 메모
    (+ 선택: 스크린샷 업로드 → vision 추출로 프리필. 없어도 동작)
 2) 채팅 UI: 유저 메시지 ↔ AI 응답(산문 + 추천 카드)
 3) 추천 카드: 도감 아이콘(캐릭터/무기/에코/소나타) + 근거 + 업그레이드 순서
 4) "이걸로 확정" 버튼 → 저장

        │ POST /ai/chat  { messages[], profile }
        ▼
[백엔드: /ai/chat]  시스템프롬프트(도감 인덱스 + 빌드/데미지 규칙 + 출력 계약) + 대화 이력
        │  OpenAI 호환 호출
        ▼
   llama-server(8080, Qwen3.6)  →  JSON 응답  { reply, recommendation?, is_final }
        │
        ▼
   프론트가 recommendation.id들로 도감 조회 → 아이콘 렌더

[확정 시] POST /ai/recommendations  → ai_recommendations 테이블
[조회]    GET  /ai/recommendations  → 기록/AI 탭에서 재열람
```

**핵심 원칙:** AI는 매 턴 recommendation을 낼 수 있으나, **저장은 항상 사용자의 "확정" 버튼으로만** 트리거된다(모델 `is_final`은 UI 힌트일 뿐). 프롬프트 인젝션/오작동으로 인한 무단 저장 방지.

## 4. 백엔드

### 4.1 엔드포인트

Stateless — 프론트가 대화 이력을 들고 매 턴 전체 전송.

```
POST /ai/chat
  { messages: [{role, content}, ...],
    profile: { union_level, owned_characters[], desired_characters[], play_style, note } }
→ { reply: str, recommendation: Recommendation|null, is_final: bool }

POST /ai/recommendations   { profile, conversation, recommendation, title } → 저장된 레코드
GET  /ai/recommendations   → 최근 레코드 목록 (user_id 스코프)
GET  /ai/recommendations/{id} → 단건
```

### 4.2 시스템 프롬프트 조립

`backend/src/ai_coach.py`가 조립:
1. **도감 인덱스** — 공명자(id↔이름↔속성/역할), 무기(id↔이름↔타입), 소나타(id↔이름↔2·5셋 효과 요약), 메인 에코 목록(3~4코스트).
2. **빌드/데미지 규칙 요약** — `build.ts`·phro.love 포뮬러 핵심(크리 기대값, 소나타 조합, 이상/속성 매핑 등).
3. **출력 계약** — 아래 JSON 스키마 + "id는 반드시 인덱스에서만 사용" 강제.
4. **profile** — 유저 인트로 입력.

### 4.3 recommendation 스키마

```jsonc
{
  "summary": "한 줄 요약",
  "team": [
    {
      "resonator_id": "...", "role": "main_dps|sub_dps|support|healer",
      "reason": "왜 이 캐릭터",
      "weapon": { "id": "...", "alt_ids": ["예산 대안"], "reason": "" },
      "echo": {
        "sonata_ids": ["5셋", "2셋"],
        "main_echo_id": "...",
        "main_stats": { "cost4": "속성피해", "cost3": "크리", "cost1": "공격%" }
      },
      "priority": 1
    }
  ],
  "upgrade_order": ["연각 X까지 → 무기 Y → 에코 파밍 ..."]
}
```

### 4.4 파싱/검증/폴백

- 응답 JSON은 기존 `parser.extract_json_object`로 파싱(```json 펜스 처리 이미 지원).
- pydantic `Recommendation` 모델로 검증. 인덱스에 없는 id는 서버가 **필터하고 경고**(하드 실패 금지 — 부분 응답 허용).
- `LLM_BASE_URL` 미설정 시 vision과 동일하게 **목업 응답** 반환.

### 4.5 신규/수정 파일

- 신규 `backend/src/ai_coach.py` — 프롬프트 조립 + LLM 호출 + 검증.
- 신규 `backend/src/ai_store.py` — 저장/목록/단건(`history.py` 패턴 복제).
- 신규 `backend/scripts/create_ai_recommendations.py` — DDL(`IF NOT EXISTS`), DEV/PROD 각 1회 실행.
- 수정 `backend/src/models.py` — `Recommendation`, `AiChatRequest`, `AiChatResponse`, `AiRecommendationRecord`.
- 수정 `backend/main.py` — 라우트 4개.

## 5. 데이터 모델

```sql
CREATE TABLE IF NOT EXISTS ai_recommendations (
  id                  TEXT PRIMARY KEY,
  user_id             TEXT,
  created_at          TIMESTAMPTZ NOT NULL,
  profile_json        JSONB NOT NULL,   -- 인트로 입력(연각/보유/스타일/메모)
  conversation_json   JSONB NOT NULL,   -- 확정 시점까지의 messages[]
  recommendation_json JSONB NOT NULL,   -- 확정된 recommendation(§4.3)
  title               TEXT              -- 목록 표시용
);
```

`ai_store.py`: `save_recommendation` / `list_recommendations(user_id, limit)` / `get_recommendation(id)` — `history.py`의 upsert·row 변환 패턴 복제. `user_id`는 history와 동일 스코프.

## 6. 프론트엔드

### 6.1 탭 변경

`constants.ts`의 `"Analyzer"` → `"Ai"`; `AppShell` 라우팅; `i18n` 라벨(ko "AI 코치" / en "AI Coach").

### 6.2 컴포넌트 (작은 단위로 분리)

- `AiCoach.tsx` — 탭 컨테이너. `phase: "intake" | "chat"`, `messages[]`, `profile`, 현재 `recommendation` 상태 관리, API 호출.
- `AiIntake.tsx` — 인트로 폼: 연각 레벨 · 캐릭터 칩(도감 resonators) · 플레이스타일 칩 · 자유 메모 · **선택적 스크린샷 업로드**(vision 프리필). 제출 시 첫 `/ai/chat` 호출.
- `AiChat.tsx` — 메시지 리스트 + 입력창. AI `reply` 산문 렌더.
- `RecommendationCard.tsx` — recommendation을 아이콘 카드로 렌더: 캐릭터별(아이콘+역할+근거) → 무기 아이콘(+예산 대안) → 소나타/메인에코 아이콘 → 메인스탯 → `upgrade_order` 순서 리스트. **"이걸로 확정" 버튼** → `saveRecommendation`.
- `CatalogIcon.tsx`(신규 공용 헬퍼) — `mediaUrl()` + `/catalog/image/{kind}/{id}` 아이콘 렌더를 추출. `Codex.tsx`/`TeamBuilder.tsx`가 이미 하던 렌더를 공유(중복 제거).

### 6.3 api.ts / 타입

- `api.ts`: `aiChat(messages, profile)`, `saveRecommendation(rec)`, `getRecommendations()`.
- `types.ts`: `AiProfile`, `AiMessage`, `Recommendation`(팀/무기/에코/업그레이드), `AiRecommendationRecord`.

### 6.4 기록 표시

확정된 추천은 기록에서 아이콘 카드로 재열람. 기존 에코-진단 기록과는 별개 섹션.

## 7. 테스트 & 검증

**백엔드 (pytest, `test_api.py` 패턴):**
- `/ai/chat` 목업 경로: `monkeypatch.delenv("LLM_BASE_URL")` → 목업 응답 구조 검증.
- 스키마 검증: 잘못된 id가 섞인 출력 → 서버 필터/경고.
- 프롬프트 조립 유닛테스트: DB 픽스처로 도감 인덱스가 id↔이름으로 생성.
- `/ai/recommendations` 저장→목록→단건 라운드트립.

**프론트엔드:** 기존 게이트대로 `tsc` + `eslint` 통과. **스크린샷 없이** 수동 칩 입력만으로 첫 호출 동작 확인.

**E2E (verify 스킬):** 실행 중인 llama-server로 실제 대화 1턴 → 유효한 recommendation JSON 파싱 + 아이콘 카드 렌더 실물 확인.

## 8. 범위 밖 (Non-goals)

- 웹 검색 / 라이브 메타 조회 (v2 후보).
- 스트리밍 응답(추후 UX 개선 시 고려).
- 다국어 추천 텍스트 — v1은 한국어 우선(모델 출력 기준).
