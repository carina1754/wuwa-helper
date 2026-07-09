# AI 코치 탭 — 구현 계획 (Implementation Plan)

- 스펙: `docs/superpowers/specs/2026-07-08-ai-coach-design.md`
- 날짜: 2026-07-08
- 브랜치: `implement-mvp`
- 접근: 아래→위(DB → 모델 → 로직 → 엔드포인트 → 프론트), 각 단계 테스트/검증 후 진행.

---

## Phase 0 — 준비 & 카탈로그 인덱스 확인

**목표:** 도감 인덱스가 프롬프트에 들어갈 형태로 뽑히는지 실데이터로 확인.

- [x] 0.1 스키마 확정: 공명자(id·name_ko·element·weapon_type·rarity·role), 무기(id·name_ko·weapon_type·rarity), 에코(id·name_ko·cost·rarity), 소나타(id·name_ko·data_json→two_piece/five_piece).
- [x] 0.2 메인 에코 = **cost 4 (75개)**. cost 1·3은 이름 인덱싱 불필요(소나타 세트+메인스탯으로 추천). 무기는 3성↑만 인덱싱.
- [x] **검증 완료:** 인덱스 실측 **7,840 토큰**(llama /tokenize), 서버 `n_ctx=32768` → 트리밍 불필요. 검증 쿼리는 Phase 2 `build_catalog_index()` 기반.

---

## Phase 1 — 데이터 모델 & 저장소 (백엔드)

**목표:** `ai_recommendations` 저장/조회가 동작.

- [ ] 1.1 `backend/scripts/create_ai_recommendations.py` — 스펙 §5 DDL(`IF NOT EXISTS`). `seed_*` 스크립트 패턴.
- [ ] 1.2 `models.py`에 추가: `Recommendation`(summary, team[], upgrade_order[]), `TeamPick`(resonator_id, role, reason, weapon, echo, priority), `WeaponPick`, `EchoPick`, `AiRecommendationRecord`, `AiProfile`, `AiMessage`, `AiChatRequest`, `AiChatResponse`.
- [ ] 1.3 `backend/src/ai_store.py` — `save_recommendation`/`list_recommendations(user_id, limit)`/`get_recommendation(id)`. `history.py` upsert·row 변환 복제.
- [ ] 1.4 **테스트** `tests/test_ai_store.py`(또는 test_api에 통합): 저장→목록→단건 라운드트립, user_id 스코프.
- [ ] **검증:** DEV DB에 `create_ai_recommendations.py` 실행 → 테이블 생성 확인. pytest 통과.

---

## Phase 2 — LLM 코치 로직 (백엔드 핵심)

**목표:** profile+messages → 검증된 `AiChatResponse`.

- [ ] 2.1 `backend/src/ai_coach.py`:
  - `build_catalog_index()` — DB에서 도감 인덱스 문자열 조립(Phase 0 기준).
  - `build_system_prompt(profile)` — 인덱스 + 빌드/데미지 규칙 요약 + 출력 계약(JSON 스키마) + profile.
  - `chat(request: AiChatRequest) -> AiChatResponse` — llama-server 호출(`vision.py`의 OpenAI 클라이언트 패턴 재사용, 이미지 없음), `parser.extract_json_object`로 파싱, `Recommendation` 검증, **인덱스에 없는 id 필터+경고**.
  - `LLM_BASE_URL` 미설정 시 목업 응답(`_mock_chat()`).
- [ ] 2.2 빌드/데미지 규칙 요약 텍스트: `build.ts`·스펙에서 핵심만 추출한 상수 문자열(크리 기대값, 소나타 조합, 속성→이상 매핑 등).
- [ ] 2.3 **테스트** `tests/test_ai_coach.py`:
  - 목업 경로(`monkeypatch.delenv("LLM_BASE_URL")`) 응답 구조.
  - 잘못된 id 섞인 가짜 모델 출력 → 필터/경고(모킹으로 LLM 응답 주입).
  - 프롬프트 조립: 인덱스에 캐릭터/무기 id·이름 포함.
- [ ] **검증:** pytest 통과.

---

## Phase 3 — 엔드포인트 노출 (백엔드)

- [ ] 3.1 `main.py` 라우트 4개: `POST /ai/chat`, `POST /ai/recommendations`, `GET /ai/recommendations`, `GET /ai/recommendations/{id}`. 기존 라우트 스타일·`response_model` 준수.
- [ ] 3.2 **테스트** `test_api.py`: `/ai/chat` 목업 200 + 스키마, `/ai/recommendations` CRUD 라운드트립.
- [ ] **검증:** 백엔드 재시작 → `curl`로 `/ai/chat`(목업) 200 확인. pytest 전체 통과.

---

## Phase 4 — 프론트 API & 타입

- [ ] 4.1 `types.ts`: `AiProfile`, `AiMessage`, `WeaponPick`, `EchoPick`, `TeamPick`, `Recommendation`, `AiRecommendationRecord`.
- [ ] 4.2 `api.ts`: `aiChat(messages, profile)`, `saveRecommendation(rec)`, `getRecommendations()`, `getRecommendation(id)`.
- [ ] **검증:** `tsc` 통과.

---

## Phase 5 — 공용 아이콘 헬퍼

- [ ] 5.1 `components/CatalogIcon.tsx` — `(kind, id, size?)` → `mediaUrl()` + `/catalog/image/...` 렌더. `Codex.tsx`/`TeamBuilder.tsx`의 기존 아이콘 렌더 로직 확인 후 추출.
- [ ] 5.2 (선택, 저위험) `Codex.tsx`/`TeamBuilder.tsx`에서 중복 아이콘 렌더를 `CatalogIcon`으로 교체 — 회귀 없는 범위에서만.
- [ ] **검증:** `tsc`+`eslint`, 도감/파티 탭 아이콘 정상 렌더.

---

## Phase 6 — AI 탭 UI

**목표:** 인트로 → 대화 → 추천 카드 → 확정.

- [ ] 6.1 `components/AiIntake.tsx` — 연각 레벨 · 캐릭터 칩(resonators) · 플레이스타일 칩 · 자유 메모 · **선택적 스크린샷 업로드**(vision 프리필, 없어도 제출 가능). 제출 → `onStart(profile)`.
- [ ] 6.2 `components/RecommendationCard.tsx` — `Recommendation` 렌더: 팀별 캐릭터/무기/에코/소나타 아이콘(`CatalogIcon`) + 근거 + 메인스탯 + `upgrade_order` 순서 리스트 + **"이걸로 확정" 버튼**.
- [ ] 6.3 `components/AiChat.tsx` — 메시지 리스트 + 입력창. AI `reply` 산문, `recommendation` 있으면 카드 삽입.
- [ ] 6.4 `components/AiCoach.tsx` — 컨테이너: `phase`(intake/chat), `messages`/`profile`/`recommendation` 상태, `aiChat` 호출, 확정 시 `saveRecommendation`.
- [ ] **검증:** `tsc`+`eslint`.

---

## Phase 7 — 탭 전환 & 배선

- [ ] 7.1 `constants.ts` `TABS`: `"Analyzer"` → `"Ai"`.
- [ ] 7.2 `AppShell.tsx`: `Ai` 탭에 `AiCoach` 렌더(기존 `Analyzer`/ScreenshotAnalyzer 자리).
- [ ] 7.3 `i18n.tsx`: 탭 라벨 + AI 코치 문자열(ko/en).
- [ ] 7.4 기록(History) 탭/패널: 확정 추천을 아이콘 카드로 재열람하는 섹션 추가(`getRecommendations`).
- [ ] **검증:** `tsc`+`eslint`, 프론트 재빌드.

---

## Phase 8 — E2E 검증 & 마무리

- [ ] 8.1 llama-server 구동 상태에서 백엔드 `LLM_BASE_URL` 설정 → 실제 `/ai/chat` 1턴 호출, 유효한 `recommendation` JSON 파싱 확인.
- [ ] 8.2 verify 스킬: 프론트에서 인트로(스크린샷 없이) → 대화 → 추천 카드 아이콘 렌더 → 확정 저장 → 기록 재열람 전체 흐름.
- [ ] 8.3 PROD DB에 `create_ai_recommendations.py` 실행(배포 전).
- [ ] 8.4 커밋/푸시. (릴리스 노트는 별도 지시 시.)

---

## 리스크 & 메모

- **모델 id 환각:** 전체 인덱스 주입 + 서버측 id 필터로 이중 방어. 필터 시 하드 실패 말고 부분 응답 허용.
- **reasoning 모델 지연:** 첫 응답이 느릴 수 있음 → 프론트 로딩 상태 명확히. 스트리밍은 v1 범위 밖.
- **에코 245개:** 3~4코스트 메인만 인덱싱해 토큰 절약. 필요 시 소나타 세트 중심으로 추가 축소.
- **저장 트리거:** 반드시 사용자 확정 버튼. 모델 `is_final`은 UI 힌트일 뿐.
