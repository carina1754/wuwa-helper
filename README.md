# 띵조 AI (WaWa AI Helper) — 스탠드얼론

비공식 워더링 웨이브(명조) 팬 도구. **한 프로세스로 도는 로컬 프로그램**입니다.
서버·도메인·로그인·DB 없이 내 PC에서 실행하고, AI 추천은 **내 NVIDIA API 키(BYO)**로 돌립니다.

기능: 도감(캐릭/무기/에코/소나타), 픽업 일정표, 캐릭터 플래너, 파티 딜 계산(자동 팀 버프),
AI 빌드 추천(대화형), 추천 기록. Wuthering Waves / Kuro Games 와 무관합니다.

## 실행 (Windows)

**쓰는 사람**: `backend\dist\띵조AI.exe` **더블클릭**. 끝. 파이썬·uv·Node·브라우저 전부 불필요,
콘솔창 없이 네이티브 창 하나 뜸. 기록은 exe 옆 `wuwa_data\` 에 파일로 저장.
(Win11 은 WebView2 기본 내장 — 없으면 MS에서 무료 설치.)

**exe 만들기** (개발자, 최초 1회 / 코드 바뀔 때만): [uv](https://docs.astral.sh/uv/) + Node.js 필요.

```powershell
.\build_exe.ps1   # 프론트 빌드 → 리소스 번들 → backend\dist\띵조AI.exe 생성
```

개발 중 빠르게 실행(빌드 없이): `backend` 폴더에서 `uv run desktop.py` (창 모드),
또는 서버만: `WUWA_HEADLESS=1 PORT=9000 uv run desktop.py` 후 브라우저로 접속.

포트는 실행 시 빈 포트를 자동으로 잡으므로 프로덕션(8000)과 충돌하지 않습니다.

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

`desktop.py`(exe 엔트리) → uvicorn 으로 FastAPI(`main:app`) 하나를 스레드에서 띄우고 pywebview 창으로 엽니다.
API 라우트 뒤에 정적 Next.js export 를 `/` 로 마운트해 **같은 포트에서 프론트+API** 를 서빙합니다.
PyInstaller onefile 이 정적·데이터(`data/`)·이미지(`media/`)를 exe 안에 번들하고, 실행 시 `_MEIPASS`
에서 읽습니다(경로는 `STATIC_DIR`/`MEDIA_DIR` env 로 주입). 기록은 exe 옆 `wuwa_data/`(`LOCAL_DATA_DIR`).
로컬 LLM·Postgres·Caddy·브라우저 모두 불필요.

## 검증

```powershell
cd backend; uv run pytest -q
cd frontend; npm run lint
```

## 안내

- 비공식 팬 도구입니다. 공식 게임 에셋은 저장소에 포함하지 않습니다.
- NVIDIA API 키는 본인이 관리하며 이 프로그램은 로컬에만 보관합니다.
