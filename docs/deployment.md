# Deployment

This project is configured for `wuwahelper.com` with Caddy as the public HTTPS reverse proxy.

## Runtime Layout

- `https://wuwahelper.com` -> Caddy
- Caddy -> Next.js on `http://127.0.0.1:3000`
- Next.js `/backend/*` rewrite -> FastAPI on `http://127.0.0.1:8000`
- NextAuth Google routes stay on the Next.js app: `/api/auth/*`

The app does not bind to TCP `443` directly. Do not run Next.js with `--experimental-https --port 443` for production.

## Frontend Environment

Create `frontend/.env.local` with:

```env
NEXTAUTH_URL=https://wuwahelper.com
AUTH_URL=https://wuwahelper.com
NEXTAUTH_SECRET=<random-secret>
AUTH_SECRET=<same-random-secret>
GOOGLE_CLIENT_ID=702566558180-f0c1hek094huhqsicrelvv5f4sfjvqun.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<google-client-secret>
ADMIN_EMAILS=wawa.ai.coach@gmail.com
NEXT_PUBLIC_API_BASE_URL=/backend
```

## Google OAuth

Google OAuth settings:

- Authorized JavaScript origin: `https://wuwahelper.com`
- Authorized redirect URI: `https://wuwahelper.com/api/auth/callback/google`

## Start App Processes

Backend:

```powershell
cd backend
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

## Start Caddy

Keep `caddy.exe` and certificate files out of Git. The expected deployment layout is:

```text
caddy/
  Caddyfile
  caddy.exe
  certs/
    wuwahelper-origin.pem
    wuwahelper-origin-key.pem
```

Run:

```powershell
cd caddy
.\caddy.exe run --config .\Caddyfile
```

`caddy/Caddyfile` terminates TLS with the files in `caddy/certs/` and reverse proxies to `127.0.0.1:3000`.

## Daily Content Refresh

The backend checks pickup schedules and update summaries once per day and writes refreshed data to SQLite. If the external source cannot be parsed, the existing DB data is kept.

Optional backend environment variable:

```env
CONTENT_REFRESH_JSON_URL=<json-feed-for-pickup-schedule-and-updates>
```

If this is set, the backend uses that JSON feed instead of article scraping. Expected shape:

```json
{
  "pickup_schedule": [],
  "game_updates": []
}
```

## DNS And Firewall

- Cloudflare `A` record: `@` -> the deployment network public IP
- Router forwards TCP `443` -> the PC running Caddy
- Windows Firewall allows inbound TCP `443` to Caddy only

For local-only testing on this PC, add this to `C:\Windows\System32\drivers\etc\hosts` as Administrator:

```text
127.0.0.1 wuwahelper.com
::1 wuwahelper.com
```
