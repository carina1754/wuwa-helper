# WaWa AI Helper

WaWa AI Helper는 한국 유저를 위한 비공식 워더링 웨이브(Wuthering Waves) 팬 도구입니다. 워더링 웨이브 업데이트 공지, 픽업 일정, 캐릭터 플래너, 스크린샷 기반 빌드 코칭 기능을 제공합니다. Wuthering Waves 또는 Kuro Games와 관련이 없습니다.

## 현재 서비스 범위

- 이 웹사이트 공지사항 및 실 서비스 준비 안내
- 한국 기준 날짜/시간과 출처 링크가 포함된 공식 워더링 웨이브 업데이트 기록
- 픽업 일정표
- 한글 라벨이 적용된 캐릭터 플래너
- NextAuth를 통한 구글 로그인
- 스크린샷 분석, 대시보드, 팀 기록, 히스토리는 업데이트 준비 중으로 일시 잠금 상태

## 실행 구조

프로덕션 환경은 Caddy를 공개용 HTTPS 리버스 프록시로 두고 그 뒤에서 동작하도록 구성되어 있습니다.

- Caddy는 `https://wuwahelper.com`에서 대기하며, 인증서 파일은 `caddy/certs/` 아래에 있습니다
- Next.js는 `127.0.0.1:3000`에서 대기합니다
- FastAPI는 `127.0.0.1:8000`에서 대기합니다
- PostgreSQL이 사용자, 공지사항, 콘텐츠 데이터, 규칙, 분석 기록을 저장합니다
- 브라우저의 `/backend/*` 요청은 Next.js가 FastAPI로 재작성(rewrite)합니다

앱 프로세스는 TCP `443` 포트에 직접 바인딩하면 안 됩니다. TLS 종료는 Caddy가 담당합니다.

## 백엔드 설정

Python 3.12와 `uv`를 사용합니다.

```powershell
cd backend
uv venv --python 3.12
uv sync --dev
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

선택적 환경 변수:

```powershell
$env:LLM_BASE_URL="http://127.0.0.1:8080/v1"   # llama.cpp llama-server (OpenAI 호환)
$env:LLM_MODEL="wuwa-vlm"
$env:LLM_API_KEY="sk-local"
$env:DATABASE_URL="postgresql://postgres:<password>@127.0.0.1:5432/wuwa_ai_coach"
$env:CORS_ALLOW_ORIGINS="https://wuwahelper.com,http://localhost:3000,http://127.0.0.1:3000"
```

비전 추출은 로컬 멀티모달 LLM(llama.cpp `llama-server`)의 OpenAI 호환 엔드포인트를 사용합니다. `LLM_BASE_URL`이 설정되어 있지 않으면 `/vision/extract`는 고정된 목(mock) 데이터를 경고 메시지와 함께 반환합니다.

백엔드 의존성을 추가할 때는 `uv add` 또는 `uv add --dev`를 사용하고, `requirements.txt` 파일을 직접 수정하지 마세요.

## 프론트엔드 설정

Node.js와 npm을 설치한 뒤, 내부 앱 서버를 실행합니다:

```powershell
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

`frontend/.env.example`을 복사해 `frontend/.env.local`을 만들고 실제 시크릿 값을 채워 넣습니다:

```env
NEXTAUTH_URL=https://wuwahelper.com
AUTH_URL=https://wuwahelper.com
NEXTAUTH_SECRET=<random-secret>
AUTH_SECRET=<same-random-secret>
GOOGLE_CLIENT_ID=<google-client-id>
GOOGLE_CLIENT_SECRET=<google-client-secret>
ADMIN_EMAILS=wawa.ai.coach@gmail.com
NEXT_PUBLIC_API_BASE_URL=/backend
```

구글 OAuth 설정:

- 승인된 자바스크립트 원본(Authorized JavaScript origin): `https://wuwahelper.com`
- 승인된 리디렉션 URI: `https://wuwahelper.com/api/auth/callback/google`

## Caddy 리버스 프록시

저장소에는 `caddy/Caddyfile`만 포함되어 있습니다. `caddy.exe`나 `caddy/certs/` 아래 파일들은 커밋하지 마세요.

배포용 PC에서 예상되는 로컬 구조:

```text
caddy/
  Caddyfile
  caddy.exe
  certs/
    wuwahelper-origin.pem
    wuwahelper-origin-key.pem
```

`caddy` 디렉터리에서 Caddy를 실행합니다:

```powershell
cd caddy
.\caddy.exe run --config .\Caddyfile
```

Caddyfile은 공개 HTTPS 트래픽을 `127.0.0.1:3000`으로 프록시합니다. FastAPI는 `127.0.0.1:8000`에서 외부에 노출되지 않고 유지됩니다.

## 실 배포 절차

배포 PC에서 아래 순서로, 각각 별도 터미널 창에서 실행합니다 (전부 포그라운드로 계속 떠 있어야 하는 프로세스입니다).

1. PostgreSQL이 실행 중인지 확인합니다. 로컬 서비스로 설치했다면 보통 Windows 부팅 시 자동으로 시작됩니다.

2. 백엔드 (터미널 1) — API 서버를 띄웁니다:

   ```powershell
   cd backend
   uv run uvicorn main:app --host 127.0.0.1 --port 8000
   ```

3. 프론트엔드 (터미널 2) — 개발 서버(`next dev`)가 아니라 **프로덕션 빌드로 실행**합니다:

   ```powershell
   cd frontend
   npm install
   npm run build
   npm run start -- --hostname 127.0.0.1 --port 3000
   ```

4. Caddy (터미널 3) — 공개 HTTPS 진입점:

   ```powershell
   cd caddy
   .\caddy.exe run --config .\Caddyfile
   ```

5. 정상 동작 확인:

   ```powershell
   curl -I https://wuwahelper.com/
   curl https://wuwahelper.com/backend/health
   ```

   첫 번째 명령은 Next.js가 사이트를 정상적으로 서빙하는지 확인합니다 (프론트엔드에는 `/health` 경로가 없으므로 그대로 요청하면 404가 납니다). 두 번째 명령은 Next.js가 `/backend/*` 요청을 FastAPI로 제대로 프록시하는지 확인합니다.

시작 전에 `backend/.env`와 `frontend/.env.local`에 실제 값(`DATABASE_URL`, `GOOGLE_CLIENT_SECRET`, `NEXTAUTH_SECRET`/`AUTH_SECRET`, `INTERNAL_API_SECRET` 등)이 모두 채워져 있어야 합니다. 두 파일의 `INTERNAL_API_SECRET`은 반드시 서로 동일한 값이어야 하며, 다르면 구글 로그인 시 유저 동기화(`POST /auth/sync-user`)가 401로 거부됩니다.

코드를 바꾼 뒤 다시 배포할 때는 백엔드/프론트엔드 프로세스를 재시작해야 반영됩니다. 프론트엔드는 소스가 바뀌었다면 `npm run build`부터 다시 실행해야 합니다 (이전 빌드 결과물이 `.next/`에 캐시되어 있기 때문입니다). 콘텐츠 데이터(공지사항, 픽업 일정, 캐릭터 정보 등)는 파일이 아니라 PostgreSQL에 직접 저장되어 있으므로, 데이터만 바꿀 때는 DB를 직접 갱신하면 되고 재배포가 필요하지 않습니다.

## 검증

백엔드:

```powershell
cd backend
uv run python -m compileall main.py src tests
uv run pytest -v
```

프론트엔드:

```powershell
cd frontend
npm run lint
```

프로덕션 빌드는 릴리스 산출물을 의도적으로 확인할 때만 실행하세요.

## 콘텐츠 데이터

모든 콘텐츠 데이터는 파일이 아니라 PostgreSQL 테이블에 직접 저장됩니다. JSON 시드 파일은 더 이상 사용하지 않습니다.

- 웹사이트 공지사항: `site_updates` 테이블
- 워더링 웨이브 업데이트: `game_updates` 테이블
- 픽업 일정: `pickup_schedule` 테이블
- 캐릭터 목록: `character_catalog` 테이블
- 빌드 규칙: `rules` 테이블
- 팀 추천 규칙: `team_rules` 테이블

## 법적/운영 관련 안내

- 이 도구는 비공식 팬 도구입니다.
- 민감한 정보가 포함된 스크린샷은 업로드하지 마세요.
- 업로드된 이미지는 기본적으로 저장되지 않습니다.
- 공식 게임 에셋은 이 저장소에 포함되어 있지 않습니다.
- HTTPS는 Caddy가 처리하며, Next.js와 FastAPI 프로세스는 localhost 전용 포트로만 열려 있어야 합니다.
