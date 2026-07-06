# WaWa AI Helper

WaWa AI Helper is an unofficial Wuthering Waves fan tool for Korean users. It provides Wuthering Waves update notices, pickup schedules, character planning, and screenshot-based build coaching. It is not affiliated with Wuthering Waves or Kuro Games.

## Current Service Scope

- Notices for this website and live-service preparation
- Official Wuthering Waves update records shown with Korea-based date/time and source links
- Pickup schedule viewer
- Character planner with Korean labels
- Google login through NextAuth
- Screenshot analysis, dashboard, team records, and history are temporarily locked while they are being updated

## Runtime Layout

Production is intended to run behind Caddy as the public HTTPS reverse proxy.

- Caddy listens on `https://wuwahelper.com` with the certificate files under `caddy/certs/`
- Next.js listens on `127.0.0.1:3000`
- FastAPI listens on `127.0.0.1:8000`
- Browser requests to `/backend/*` are rewritten by Next.js to FastAPI

The app process must not bind to TCP `443` directly. TLS termination belongs to Caddy.

## Backend Setup

Use Python 3.12 with `uv`.

```powershell
cd backend
uv venv --python 3.12
uv sync --dev
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Optional environment variables:

```powershell
$env:OPENAI_API_KEY="..."
$env:OPENAI_MODEL="gpt-4.1-mini"
$env:DATABASE_URL="sqlite:///./wuwa_ai_coach.db"
$env:CORS_ALLOW_ORIGINS="https://wuwahelper.com,http://localhost:3000,http://127.0.0.1:3000"
```

If `OPENAI_API_KEY` is not set, `/vision/extract` returns `backend/data/sample_extraction.json` with a mock-mode warning.

To add backend dependencies, use `uv add` or `uv add --dev`; do not edit a `requirements.txt` file.

## Frontend Setup

Install Node.js with npm, then run the internal app server:

```powershell
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Create `frontend/.env.local` from `frontend/.env.example` and set real secrets:

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

Google OAuth settings:

- Authorized JavaScript origin: `https://wuwahelper.com`
- Authorized redirect URI: `https://wuwahelper.com/api/auth/callback/google`

## Caddy Reverse Proxy

The repository includes `caddy/Caddyfile` only. Do not commit `caddy.exe` or anything under `caddy/certs/`.

Expected local layout on the deployment PC:

```text
caddy/
  Caddyfile
  caddy.exe
  certs/
    wuwahelper-origin.pem
    wuwahelper-origin-key.pem
```

Start Caddy from the `caddy` directory:

```powershell
cd caddy
.\caddy.exe run --config .\Caddyfile
```

The Caddyfile proxies public HTTPS traffic to `127.0.0.1:3000`. FastAPI remains private on `127.0.0.1:8000`.

## Verification

Backend:

```powershell
cd backend
uv run python -m compileall main.py src tests
uv run pytest -v
```

Frontend:

```powershell
cd frontend
npm run lint
```

Run a production build only when intentionally checking a release artifact.

## Content Data

- Website notices: `backend/data/site_updates.json`
- Wuthering Waves updates: `backend/data/game_updates.json`
- Pickup schedules: `backend/data/pickup_schedule.json`
- Character catalog: `backend/data/character_catalog.json`
- Build rules: `backend/data/build_rules.json`

## Legal and Operational Notes

- This is an unofficial fan tool.
- Do not upload screenshots containing sensitive information.
- Uploaded images are not stored by default.
- Official game assets are not bundled in this repository.
- Caddy handles HTTPS; the Next.js and FastAPI processes should stay on localhost-only ports.
