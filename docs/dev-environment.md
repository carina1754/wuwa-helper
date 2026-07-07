# 개발 환경 (실 서버와 분리)

실 서버는 포트 3000(Next)/8000(FastAPI)과 DB `wuwa_ai_coach`를 사용합니다.
개발은 아래처럼 **별도 DB + 별도 포트**로 완전히 분리해 실행합니다.

## 1. 개발용 DB 생성 (최초 1회)

```powershell
psql -U postgres -c "CREATE DATABASE wuwa_ai_coach_dev;"
```

스키마는 백엔드 최초 기동 시 `init_db()`가 자동 생성합니다.

## 2. 백엔드 (포트 8001, 개발 DB)

```powershell
cd backend
$env:DATABASE_URL="postgresql://postgres:<password>@127.0.0.1:5432/wuwa_ai_coach_dev"
uv run uvicorn main:app --host 127.0.0.1 --port 8001
```

## 3. 프론트엔드 (포트 3001, 8001로 프록시)

```powershell
cd frontend
$env:BACKEND_ORIGIN="http://127.0.0.1:8001"
$env:NEXT_PUBLIC_API_BASE_URL="/backend"
npm run dev -- --hostname 127.0.0.1 --port 3001
```

브라우저에서 http://127.0.0.1:3001 로 접속합니다.

## 4. 명조 업데이트 데이터 채우기

개발 DB는 비어 있으므로, 백엔드가 뜬 상태에서 강제 새로고침을 한 번 호출합니다
(공식 기사 + 대표 이미지 다운로드, 이어서 큐레이션 요약 반영):

```powershell
curl -X POST http://127.0.0.1:8001/content/refresh
curl http://127.0.0.1:8001/updates
```

## 5. 백엔드 테스트 (개발 DB 대상)

```powershell
cd backend
$env:DATABASE_URL="postgresql://postgres:<password>@127.0.0.1:5432/wuwa_ai_coach_dev"
uv run pytest -v
```

> 테스트/새로고침은 DB를 변경하므로 반드시 `wuwa_ai_coach_dev`를 가리킨 상태에서
> 실행하세요. 실 DB(`wuwa_ai_coach`)를 가리키면 실 데이터가 바뀝니다.
