# 띵조 AI

비공식 워더링 웨이브(명조) 팬 도구. **더블클릭 한 번으로 뜨는 네이티브 Windows 프로그램**입니다.
서버·도메인·로그인·DB 없이 내 PC에서 실행하고, AI 추천은 **내 NVIDIA API 키(BYO)**로 돌립니다.
Wuthering Waves / Kuro Games 와 무관합니다.

- UI: PySide6(Qt6) 네이티브 창, 토스(TDS)풍 디자인, 한국어 전용
- 탭: **AI 빌딩**(대화형 빌드 추천) · **도감**(캐릭/무기/에코) · **픽업 일정**(배너 그룹·D-day) ·
  **업데이트**(패치 요약) · **파티**(팀 딜 계산 — 공명 사슬·팀 버프 자동, 결과는 기록 탭에 자동 저장) ·
  **기록** · **설정**
- 딜 계산은 로컬 시뮬 엔진(`backend/src/sim`)을 직접 호출 — 네트워크 불필요

## 쓰는 사람 (배포)

1. `backend\dist\띵조AI.exe` 를 받아 **더블클릭**. 끝. (파이썬·Node·브라우저 설치 불필요, 콘솔창 없음)
2. AI 기능을 쓰려면 앱 **설정 탭**에 NVIDIA API 키 입력:
   - https://build.nvidia.com 에서 무료 발급 (`nvapi-...`)
   - 키 붙여넣기 → **모델 불러오기** → 모델 선택
   - 키·모델·기록 등 내 데이터는 전부 이 PC 의 `%LOCALAPPDATA%\띵조AI` 에 JSON 으로만 저장(외부 전송 없음, 폴더 삭제 = 초기화)
3. 키가 없어도 AI 빌딩 탭만 안내 모드일 뿐, 나머지 기능은 전부 오프라인으로 정상 동작

**배포 = 이 exe 파일 하나를 전달하면 끝.** 설치 과정 없음.

## 개발 환경

Windows 11 + [uv](https://docs.astral.sh/uv/) (Python 3.13 자동 관리). Node 불필요.

```powershell
cd backend
uv sync                          # 의존성 설치 (PySide6 포함)
uv run python run_native.py      # 개발 실행 — 빌드 없이 네이티브 창
```

검증:

```powershell
uv run pytest -q                         # 엔진/API 테스트
uv run python -m native.tabs.pickup      # 탭별 헤드리스 스모크 (teams / codex / ai / updates / history 동일)
```

코드 배치:

- `backend/native/` — 데스크톱 앱 전체 (app·theme·widgets·tabs, 엔진 직접 호출·HTTP 없음)
- `backend/src/` — 딜 시뮬 엔진·카탈로그·AI 코치·로컬 저장소(`localstore`)
- `backend/data/catalog/*.json` — 캐릭/무기/에코/소나타 **정본 데이터**(datamine 파리티 검증본, DB 불필요)
- `backend/data/content/*.json` — 픽업 배너·게임 업데이트 콘텐츠
- `frontend/`, `backend/src/api/`, `backend/desktop.py` — 구 웹 서비스(wuwahelper.com) 레거시. 신규 개발은 `native/` 에서

## exe 빌드 (배포판 만들기)

```powershell
.\build_exe.ps1     # PyInstaller onefile → backend\dist\띵조AI.exe (약 130MB)
```

- 스펙: `backend/app.spec` — 데이터(`data/`)·이미지(`media/`) 번들, 콘솔 없음(windowed)
- `build_exe.ps1` 은 ASCII 전용(PowerShell 5.1 이 비ASCII 소스를 오파싱) — 한글 제품명은 spec 안에만
- 빌드 후 exe 더블클릭으로 부트 확인 권장

## 안내

- 비공식 팬 도구입니다. 공식 게임 에셋은 저장소에 포함하지 않습니다.
- NVIDIA API 키는 본인이 관리하며 이 프로그램은 로컬에만 보관합니다.
