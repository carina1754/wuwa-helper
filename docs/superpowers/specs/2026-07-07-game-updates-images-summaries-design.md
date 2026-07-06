# Game Updates: Official Hero Image + Curated Korean Summary Design

## Problem

The `game_updates` feature (명조 / Wuthering Waves version update log) currently
shows only a version badge, a generic title (`"3.4 업데이트"`), an optional
release date, and source links. `backend/src/content_refresh.py` discovers
version-update articles from the official Kurogame news JSON but leaves
`summary_ko` and `highlights_ko` empty, and there is no representative image.
All 19 existing `game_updates` rows have empty summaries and no image.

The goal is to make each update entry show (1) the official representative
banner image and (2) a readable Korean summary + highlights of what the
version contains.

## Goal

1. Cache each version's official hero banner image on the server and serve it
   from our own domain; expose it to the frontend via a new `image_url` field.
2. Populate a human-authored Korean `summary_ko` + `highlights_ko` for each
   version that has an official article, stored in the DB.
3. Improve `title_ko` to the official thematic title
   (e.g. `「선택하지 않은 꿈」 3.4 버전`) instead of the generic `"{version} 업데이트"`.
4. Ensure the daily refresh never wipes the authored summaries.
5. Display image + summary + highlights in the Updates UI.
6. Provide an isolated dev environment (separate DB + ports) so development
   never touches the live production data.

## Non-goals / Out of scope

- **No runtime LLM/OpenAI call for summarization.** Summaries are authored (by
  Claude / curator) and committed, then applied to the DB. A future automated
  generator can replace the authoring step later; the storage/display contract
  is unchanged. ("일단" — for now — this feature area does not use the AI API.)
- **No `TEXT` → `JSONB` storage-format migration.** The existing
  document-in-Postgres pattern (`data_json TEXT` holding the serialized Pydantic
  model) is kept as-is. All content continues to live in PostgreSQL — no
  file-based storage is reintroduced.
- No admin editing UI, no image thumbnailing/resizing, no multi-language
  summaries, no historical backfill beyond versions that have official articles.
- Character/weapon catalog work is unrelated to this change. (Noted only because
  the user confirmed all character/weapon info must also live in the DB — that is
  already the case via `character_catalog` and is unaffected here.)

## Data source (verified)

Official Kurogame news JSON, already used by `content_refresh.py`:

- Menu/list: `https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/{locale}/MainMenu.json`
  → `article[]` with `articleId`, `articleTitle`, `startTime`, `suggestCover`.
- Detail: `.../{locale}/article/{articleId}.json` → `articleContent` (HTML),
  `articleTitle`.

Verified during design:

- Version-content articles ("X.Y 버전 내용 안내", `articleType` 65) are matched
  by the existing `_is_version_update_article` patterns.
- Each such article's `articleContent` contains exactly **one** `<img src>` —
  the hero banner at the top (e.g. 3.4 →
  `https://hw-media-cdn-mingchao.kurogame.com/object/.../...jpg`). The list-level
  `suggestCover` is empty for these articles, so the content's first image is the
  representative image.
- The image URL is publicly fetchable (HTTP 200, `image/jpeg`, ~7 MB) with the
  existing `WuWaHelper/1.0` User-Agent.
- The article body is rich structured Korean text (점검 시간/보상, 신규·콜라보
  캐릭터, 신규 무기, 이벤트, QoL) — the basis for the authored summary.

## Data model change

Add one nullable field to `GameUpdateSummary` (`backend/src/models.py`) and the
matching `GameUpdateSummary` interface in `frontend/src/lib/types.ts`:

```
image_url: str | None = None   # API-relative path of our cached image,
                               # e.g. "/updates/image/wuwa-3-4"; null if none
```

No DB schema migration: the field is serialized into the existing
`game_updates.data_json` blob and restored by
`GameUpdateSummary.model_validate_json(...)`. `version` and `release_date_kst`
remain duplicated into their own sort/index columns exactly as today.

## Storage / ownership model

Everything is stored in PostgreSQL (`game_updates.data_json`), consistent with
the "all content in Postgres" policy. Two owners for a row's fields:

| Field | Owner | On refresh |
|---|---|---|
| version, release_date_kst, title_ko, source_links, image_url | refresh (derived from official source) | refreshed each run |
| summary_ko, highlights_ko | curated (authored) | **preserved** — never overwritten with empty |

## Backend — image caching

- Media dir: `MEDIA_DIR` env, default `backend/media`. Add `backend/media/`
  (and generic `media/`) to `.gitignore`; assets are never committed.
- During refresh, for a version whose row has no cached image yet: extract the
  first `<img src>` from `articleContent`, download it (timeout + max-size
  guard, reusing the existing `Request(..., headers={"User-Agent":
  "WuWaHelper/1.0"})` pattern), and save to `MEDIA_DIR/updates/{id}{ext}` where
  `ext` is derived from the URL / content-type (default `.jpg`).
- Set `image_url = "/updates/image/{id}"` on the stored item.
- New route in `main.py`: `GET /updates/image/{id}` → resolve
  `MEDIA_DIR/updates/{id}.*`, return `FileResponse` with a long `Cache-Control`;
  404 when absent.
- Frontend loads it as `` `${API_BASE_URL}${update.image_url}` `` — through the
  `/backend` rewrite in prod, and `/backend` → `127.0.0.1:8001` in dev.

## Backend — curated summaries + idempotent apply

- New module `backend/src/curated_updates.py`:

  ```
  CURATED_UPDATE_SUMMARIES: dict[str, dict] = {
      "3.4": {"summary_ko": "...", "highlights_ko": ["...", ...]},
      ...
  }
  ```

  keyed by version string. This is the source of truth for authored summaries so
  they survive a DB reset (the dev DB starts empty) and deploy to prod alongside
  the code. It is small, feature-specific editorial text — categorically
  different from the removed full-dataset seed dump.
- `apply_curated_update_summaries()`: idempotent. For each version present in
  both `CURATED_UPDATE_SUMMARIES` and the `game_updates` table, update that row's
  `data_json` so `summary_ko`/`highlights_ko` match the module. Runs on startup
  and after each refresh; a second run is a no-op.

## Refresh changes (`content_refresh.py`)

1. Extract the thematic `title_ko` from the official article title (strip
   trailing "내용 안내" / "버전 내용 안내" boilerplate, keeping e.g.
   `「선택하지 않은 꿈」 3.4 버전`); fall back to `"{version} 업데이트"` when no
   article title is available.
2. In the `game_updates` upsert loop, before writing each item, read the
   existing row's `summary_ko`/`highlights_ko` and carry them forward when the
   freshly-built item's are empty — so refresh never blanks authored summaries.
3. Cache the hero image (above) and set `image_url`.
4. After the upserts, call `apply_curated_update_summaries()`.

Because `_updates_from_official_articles` still returns empty summaries, the
preserve step (2) and `apply_curated_update_summaries` (4) together guarantee the
DB always ends with the authored summaries, regardless of ordering.

## Frontend — `UpdatesSummary.tsx`

- Add `image_url?: string | null` to the `GameUpdateSummary` type.
- When `image_url` is set, render the hero image at the top of the card:
  `<img src={`${API_BASE_URL}${image_url}`} loading="lazy" ... />` with a fixed
  aspect ratio and `object-cover`, matching existing `<img>` usage
  (`CharacterPlanner.tsx` / `PickupSchedule.tsx`) — no `next/image`, so no domain
  allowlist is needed.
- Keep the existing summary / highlights / source-link layout below the image.
- Versions with no image and an empty summary (e.g. a future 3.5 with no article
  yet) degrade gracefully: version badge + title + date + source only.

## Dev environment isolation

Live production keeps 3000 (Next) / 8000 (FastAPI) / `wuwa_ai_coach` DB. Dev
runs fully separate so refresh + summary work never touches production data:

- **DB**: create an empty `wuwa_ai_coach_dev`; `init_db()` auto-creates the
  schema on first backend start.
- **Backend**: port **8001**, `DATABASE_URL=postgresql://.../wuwa_ai_coach_dev`.
- **Frontend**: port **3001**; `NEXT_PUBLIC_API_BASE_URL=/backend`.
- **Proxy**: make the `next.config.ts` rewrite destination env-driven —
  `process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000"`; dev sets
  `BACKEND_ORIGIN=http://127.0.0.1:8001`.
- Document the exact dev commands (and any `.env.dev` values / npm scripts) so
  both servers start on the dev ports against the dev DB.
- The dev backend's refresh worker fetches official data + images into the dev
  DB only; `POST /content/refresh` can be triggered manually to populate on
  demand. `DISABLE_CONTENT_REFRESH=1` is optional if the daily worker is not
  wanted in dev.

## Testing

Backend (`backend/tests/`, mirroring `test_content_refresh.py`; no network —
use fixtures/stubs, no real OpenAI or HTTP calls):

- Hero-image URL extraction from a sample `articleContent`.
- Thematic `title_ko` extraction and fallback.
- Refresh preserves an existing authored `summary_ko`/`highlights_ko` when the
  scraped item is empty (seed a row, run refresh with a stubbed article payload,
  assert the summary survives alongside refreshed metadata).
- `apply_curated_update_summaries()` fills matching rows and is a no-op on a
  second run.
- `GET /updates/image/{id}` returns a cached file and 404s when missing (using a
  temp `MEDIA_DIR`).

Existing `uv run pytest` stays green; `npm run lint` stays clean.

## Rollout / authoring workflow

- First dev run: create `wuwa_ai_coach_dev`, start backend (8001) + frontend
  (3001), trigger a manual refresh to populate versions + cache images, then
  `apply_curated_update_summaries()` fills the authored text.
- Authoring: for each version with an official article, read `articleContent`
  and write `summary_ko` + `highlights_ko` into `CURATED_UPDATE_SUMMARIES`. This
  change ships authored summaries for the recent 3.x versions; older versions can
  be added later by extending the module.
- Prod: on deploy, the same `apply_curated_update_summaries()` runs on
  startup/refresh against the prod DB, so the authored summaries land in
  production without a separate manual DB edit.
