# 무료 스탠드얼론 배포판 설계 (BYO NVIDIA 키 · Postgres 제거 · 로그인 제거)

날짜: 2026-07-14
브랜치: implement-mvp
상태: 설계 승인 대기

## 배경 / 목표

wuwahelper.com은 현재 이 Windows 머신에서 24/7 구동(Caddy 443 → next start 3000 → FastAPI 8000 → 로컬 llama-server 8080, Postgres). 운영비(전기 + GPU 상시 + 도메인)를 감당하기 어려워, **유저가 내려받아 로컬 실행하는 프로그램**으로 배포하려 한다.

핵심 제약: 35B GGUF 로컬 모델은 앱에 못 넣는다(~20GB, GPU 필수). 따라서 AI는 **유저 본인 NVIDIA NIM API 키**(무료 티어, OpenAI 호환 `https://integrate.api.nvidia.com/v1`)로 대체한다.

목표: **운영비 0.** Postgres 없이, 로컬 llama 없이, 로그인 없이 도는 스탠드얼론.

## 타당성 검증 (실측 완료)

- NVIDIA NIM = OpenAI 호환. 기존 `OpenAI(base_url, api_key, model)` 클라이언트 그대로 재사용.
- `GET /v1/models` → 121개 모델(드롭다운 소스).
- `response_format={"type":"json_object"}` 구조출력 동작(앱 계약 유지). `meta/llama-3.3-70b-instruct`·`nvidia/llama-3.3-nemotron-super-49b-v1.5` 둘 다 valid JSON + 한국어 정상.
- ⚠️ 무료 티어 지연 40~60초/턴(실측). 무료 대가로 수용, 빠른 기본 모델 선정.

## 결정 사항 (사용자 확정)

1. **스크린샷 분석 기능 드롭** — `/vision/extract`·`/analyze/*`·`/history`(analysis_sessions)·`evaluator`·`rules` 전부 제거. 현재 프론트 UI서 호출 안 함(스냅샷딜 탭 폐지 때 死). 죽은 코드라 손실 없음.
2. **설정 UI = 전용 '설정' 탭** 신설.

## 불변 계약 (유지)

- AI 대화 출력·LLM 프롬프트 페이로드는 **한국어 유지**. 표시 크롬만 4언어 현지화(기존 i18n).
- 딜 엔진 키(SkillType, damage[].name)·카탈로그 한국어 유지.
- 카탈로그는 이미 파일 정본(`backend/data/catalog/*.json`, `@lru_cache`) — 그대로.

---

## Part A — BYO NVIDIA 키 + 모델 선택

### 백엔드

- **키 전달 = HTTP 헤더**(`X-LLM-Key`, `X-LLM-Model`). 요청 본문/Pydantic 모델 밖으로 빼서 기록·직렬화 경로에 절대 안 섞이게 함. **키는 서버 저장·로그·기록 절대 금지.**
- `ai_coach.chat(request, *, api_key=None, model=None, base_url=None)` — 우선순위 `요청 헤더 > env > 기본`. base_url 기본 `https://integrate.api.nvidia.com/v1`.
- `main.py` `/ai/chat`가 `Header(None)`로 키·모델 읽어 `chat()`에 전달.
- 새 엔드포인트 **`GET /ai/models`** — `X-LLM-Key` 헤더 받아 NVIDIA `/v1/models` 프록시(브라우저 CORS 회피). embed/safety/reranking/vlm-embed 계열 필터, 채팅 가능 id만 반환.

### 프론트

- 새 **`설정` 탭** + `components/Settings.tsx`:
  - 키 입력(password 필드) → `localStorage["nvidia_api_key"]`.
  - "모델 불러오기" → `GET /ai/models`(헤더) → 드롭다운 → `localStorage["nvidia_model"]`.
  - 유효성 표시(모델 로드 성공/실패).
- `lib/api.ts` `aiChat()`·`getModels()`가 localStorage 키·모델을 `X-LLM-Key`/`X-LLM-Model` 헤더로 동봉.
- `AppShell` TABS에 설정 탭 등록. i18n(ko/en/ja/zhHans) 문자열 추가.
- AI 코치 UI: 키 미설정 시 "설정 탭에서 NVIDIA 키 등록" 안내.

---

## Part B — SQL 제거 → 로컬 파일

### 신규 `backend/src/localstore.py`

소형 JSON 파일 저장소. `data_dir()`(기본 `backend/data/local/`, env `LOCAL_DATA_DIR` override), `read_json(name, default)`, `write_json(name, obj)`(temp+os.replace 원자적 쓰기).

### 전환

- **`ai_store.py`** → localstore. 추천 기록을 `ai_recommendations.json` 리스트로 save/list/get/delete. **user_id 스코프 제거**(단일 로컬 유저 — 인자 무시, 전체 반환).
- **`content.py`**(pickups·game_updates·site_updates·game_config) → 정적 스냅샷 JSON 파일 읽기. `backend/data/content/{pickup_schedule,game_updates,site_updates,game_config}.json`. `refresh_pickups_and_updates_if_stale` → no-op.
  - 1회 export 스크립트 `scripts/export_content_to_files.py`(현재 DB → 4파일). 지금 DB 살아있을 때 실행해 파일 생성·커밋. (content는 DB 정본이 맞음: game_updates는 curated i18n이 DB에 머지됨, site_updates는 시드 스크립트가 DB에 씀.)
- **로그인 제거**:
  - 백엔드: `users.py`·`/auth/sync-user`·`login_events`·`require_internal_secret` 삭제. user_id 사용처 제거.
  - 프론트: next-auth 전부 삭제 — `auth.ts`·`app/api/auth/*`·`app/login/page.tsx`·`app/admin` 게이팅·`types/next-auth.d.ts`·`lib/backendUser.ts`·`lib/accountId.ts`·`providers.tsx`의 `SessionProvider`(LanguageProvider만 남김)·`app/backend/ai/recommendations/*` 프록시(유저 주입) 단순화. `AiCoach`/`AiHistory`서 useSession 제거, user_id 없이 저장·조회.
- **스크린샷 분석 드롭**(결정1): `vision.py`·`evaluator.py`·`rules.py`·`history.py`·`parser.py`(비전 전용이면)·`optional_*` + `main.py` `/vision`·`/analyze/*`·`/history`·`/rules`·`/report` 엔드포인트 + `api.ts` 대응 함수 + 죽은 모델 제거.
- **`database.py`·`init_db()` 삭제**. `main.py` init_db 호출·psycopg 임포트 제거. datamine 스키마 init 런타임서 제거(추출 스크립트는 독립 유지).

### 남는 런타임 파일 의존

`backend/data/catalog/*.json`(카탈로그) + `backend/data/content/*.json`(픽업·업뎃·config) + `backend/data/local/*.json`(AI 기록, 런타임 생성). Postgres·psycopg 의존 0.

---

## Part C — 실제 패키징(.exe/앱) — **이번 범위 제외**

A+B로 클라우드·DB 의존 0 달성 후 별도 진행. 후보: Tauri(경량) / PyInstaller + 정적 Next export / run.bat + 임베디드 파이썬. 그때 결정.

---

## 검증

- **Postgres 정지 상태**로 백엔드 부팅 성공(무DB 증명).
- `/ai/models`(헤더 키) → 모델 목록. `/ai/chat`(헤더 키·모델) → 실제 NVIDIA 응답.
- codex·pickups·updates·party 전부 파일서 서빙(무DB).
- AI 기록 로컬 파일 저장·재시작 후 유지.
- `npx tsc --noEmit`·eslint·`npm run build`·pytest green.

## 리스크

- 무료 티어 지연 40~60초/턴(수용).
- content 스냅샷 프리즈(오프라인 툴이라 허용, 앱 업데이트로 갱신).
- 프론트 next-auth 제거가 16파일 관여 — 구현 시 useSession 사용처 전수 추적 후 편집(systematic).
