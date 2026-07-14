# 띵조 AI (WaWa AI Helper) — 스탠드얼론

비공식 워더링 웨이브(명조) 팬 도구. **한 프로세스로 도는 로컬 프로그램**입니다.
서버·도메인·로그인·DB 없이 내 PC에서 실행하고, AI 추천은 **내 NVIDIA API 키(BYO)**로 돌립니다.

기능: 도감(캐릭/무기/에코/소나타), 픽업 일정표, 캐릭터 플래너, 파티 딜 계산(자동 팀 버프),
AI 빌드 추천(대화형), 추천 기록. Wuthering Waves / Kuro Games 와 무관합니다.

## 실행 (Windows)

준비물: [uv](https://docs.astral.sh/uv/) (파이썬 자동 관리), 그리고 최초 1회 빌드용 Node.js.

```powershell
# 1) 최초 1회: 프론트 정적 빌드 → backend/static 생성
.\build.ps1

# 2) 실행 — 이후엔 이것만
```

- **`띵조AI.vbs` 더블클릭** — 콘솔창 없이 **네이티브 창**으로 뜸(브라우저 X). 권장.
- 또는 `start.bat` 더블클릭 (콘솔창 같이 뜸, 로그 확인용).
- 또는 브라우저로 열고 싶으면 backend 폴더에서 `uv run run.py` (기본 `http://127.0.0.1:9000/`).

포트는 `desktop.py` 가 빈 포트를 자동으로 잡으므로 프로덕션(8000)과 충돌하지 않습니다.
Windows 는 WebView2 런타임이 필요한데 Win11 엔 기본 내장입니다(없으면 MS에서 무료 설치).

> 코드(프론트)를 고쳤을 때만 `.\build.ps1` 을 다시 돌리면 됩니다. 데이터·백엔드 수정은 재빌드 불필요.

## AI 설정 (NVIDIA BYO 키)

로그인이 없으므로 AI 기능은 앱 안 **'설정' 탭**에서 키를 넣어야 동작합니다.

1. https://build.nvidia.com 에서 API 키 발급 (`nvapi-...`)
2. 앱 → **설정** 탭 → 키 붙여넣기 → **모델 불러오기** → 모델 선택
3. 키·모델은 **브라우저 localStorage 에만** 저장됩니다(서버에 저장/전송·기록 안 됨).
   요청 시 `X-LLM-Key` / `X-LLM-Model` 헤더로만 실려 나갑니다.

키가 없으면 AI 탭은 목(mock) 폴백 응답을 돌려줍니다.

## 데이터 저장 (파일, DB 없음)

- 카탈로그 정본: `backend/data/catalog/*.json`
- 콘텐츠(공지·픽업 등): `backend/data/content/*.json`
- AI 추천 기록: `backend/data/local/ai_recommendations.json` (실행 중 생성, git 제외)

`LOCAL_DATA_DIR` 로 기록 경로를 옮길 수 있습니다.

## 구조

`run.py` → uvicorn 이 FastAPI(`main:app`) 하나만 띄웁니다.
API 라우트 뒤에 `backend/static`(빌드된 Next.js export)을 `/` 로 마운트해 **같은 포트에서 프론트+API** 를 서빙합니다. 로컬 LLM·Postgres·Caddy 모두 불필요.

## 검증

```powershell
cd backend; uv run pytest -q
cd frontend; npm run lint
```

## 안내

- 비공식 팬 도구입니다. 공식 게임 에셋은 저장소에 포함하지 않습니다.
- NVIDIA API 키는 본인이 관리하며 이 프로그램은 로컬에만 보관합니다.
