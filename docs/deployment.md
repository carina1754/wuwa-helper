# Deployment

This project is configured to run from this Windows PC with `wawahelper.com` as the public domain.

## Runtime Layout

- `https://wawahelper.com` -> Next.js frontend on port `443`
- `https://wawahelper.com/api/auth/*` -> NextAuth Google login routes
- `https://wawahelper.com/backend/*` -> Next.js rewrite to FastAPI on `http://127.0.0.1:8000`

This keeps browser API calls on the same HTTPS origin and avoids mixed-content errors.

## Frontend Environment

Create `frontend/.env.local` with:

```env
NEXTAUTH_URL=https://wawahelper.com
AUTH_URL=https://wawahelper.com
NEXTAUTH_SECRET=<random-secret>
AUTH_SECRET=<same-random-secret>
GOOGLE_CLIENT_ID=702566558180-f0c1hek094huhqsicrelvv5f4sfjvqun.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<google-client-secret>
ADMIN_EMAILS=wawa.ai.coach@gmail.com
NEXT_PUBLIC_API_BASE_URL=/backend
```

## Google OAuth

Google OAuth settings:

- Authorized JavaScript origin: `https://wawahelper.com`
- Authorized redirect URI: `https://wawahelper.com/api/auth/callback/google`

## Start On This PC

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-server.ps1
```

This starts:

- FastAPI: `http://127.0.0.1:8000`
- Next.js HTTPS: `https://wawahelper.com`

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

## Cloudflare DNS

If you want other devices on the internet to reach this PC, Cloudflare must point `wawahelper.com` to this network.

Option A: Public IP + router port forwarding

- Cloudflare `A` record: `@` -> your public IP
- Router forwards TCP `443` -> this PC
- Windows Firewall allows inbound TCP `443`

Option B: Cloudflare Tunnel

- Run `cloudflared` on this PC
- Route `wawahelper.com` to `https://localhost:443`
- No router port forwarding is needed

For local-only testing on this PC, add this to `C:\Windows\System32\drivers\etc\hosts` as Administrator:

```text
127.0.0.1 wawahelper.com
::1 wawahelper.com
```
