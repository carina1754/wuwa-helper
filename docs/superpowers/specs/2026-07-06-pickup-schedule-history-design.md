# Pickup Schedule Historical Backfill Design

## Problem

`backend/data/pickup_schedule.json` only has partial 2026 data, and the 2026-01
through 2026-04 entries are placeholder/example data (`notes_ko` literally says
"첨부 예시 기준" — "based on the attached example"), not real game data. Only
the 2026-07 entries (sourced from PC Gamer) are real. There is no 2024 or 2025
data at all, even though Wuthering Waves launched in May 2024.

Separately, `backend/src/content_refresh.py::refresh_pickups_and_updates`
does `DELETE FROM pickup_schedule` before inserting whatever the current
scrape returns. Since the scrape source (PC Gamer's "current/next" banner
page) only ever contains the current one or two months of banners, every
successful refresh permanently destroys all older rows — including any
historical backfill this design adds.

## Goal

1. Replace the fake placeholder rows and fill in every real character pickup
   banner from launch (version 1.0, May 2024) through the present, stored in
   the existing `pickup_schedule` SQLite table.
2. Fix the refresh bug so future daily scrapes only add/update the current
   period's rows and never delete historical rows.

## Out of scope

- `game_updates` (version update summaries) historical backfill — deferred.
- Weapon banners — the existing schema and UI only track character banners.
- Naver Game Lounge integration — `game.naver.com` itself is blocked by
  browser-automation tooling policy, and its underlying API
  (`comm-api.game.naver.com`) requires further endpoint discovery that wasn't
  completed. The existing PC Gamer scraper already works and stays as the
  live "current/next" source.

## Data source for backfill

Historical banner data (character, debut vs. rerun, version, phase date
range) compiled from game8.co's "All Gacha Banner History" guide
(`https://game8.co/games/Wuthering-Waves/archives/494979`), which covers
version 1.0 (May 2024) through 3.5 (August 2026) with per-phase debut/rerun
detail. This is a one-time research pass, not a live scraper — past banners
are historical fact and don't need re-fetching once recorded.

## Mapping into the existing schema

`PickupScheduleItem` only has `id, year, month, category
(first_pickup|rerun_1|rerun_2), label_ko, characters[], notes_ko,
source_links[]` — no exact dates or version field, and the frontend
(`PickupSchedule.tsx`) only ever groups by `year` + `month` and renders each
row's character avatars under its category label. No schema changes are
needed; richer per-phase date/version detail is not rendered anywhere, so it
is dropped rather than carried through.

Conversion rule, applied per version-phase from the game8 history:

- Bucket each phase by the **year/month of its start date**.
- Characters marked "Debut" in a phase go into a `first_pickup` row for that
  year/month.
- Characters marked "Rerun" that run concurrently with a debut in the same
  phase go into a `rerun_1` row for the same year/month (this matches the
  existing convention already used by the one real seeded example:
  2026-07 has Lucy/Rebecca as `first_pickup` and Lucilla/Cartethyia as a
  separate `rerun_1` for the same month).
- A phase with no debut character (pure rerun phase) still produces a
  `rerun_1` row (or `rerun_2` if another phase already filled `rerun_1` for
  that same year/month).
- If a calendar month contains two phases that each have a debut (this
  happens when a version's two phases fall in the same month), merge their
  debut characters into one `first_pickup` row rather than creating a
  second row with a duplicate category label.
- 4-star characters and weapon banners are not recorded, matching the
  existing data shape (only 5-star rate-up characters are listed today).
- Each row's `source_links` cites the game8 history page; `notes_ko`
  briefly states the version/phase this row came from (in Korean, matching
  existing style).

## Refresh bug fix

In `content_refresh.py::refresh_pickups_and_updates`, replace the
`DELETE FROM pickup_schedule` + bulk-insert with an upsert
(`INSERT OR REPLACE`) keyed by `id`, touching only the rows present in the
freshly scraped payload. Historical rows whose `id` isn't part of the
current scrape result are left untouched. The same change applies to
`game_updates` for consistency, even though its historical backfill is out
of scope for this change.

## Testing

- Extend `backend/tests/test_api.py` (or a new
  `backend/tests/test_content_refresh.py`) with a test that: seeds a
  historical row directly in the `pickup_schedule` table, runs
  `refresh_pickups_and_updates` with a stubbed/mocked scrape result for a
  different year/month, and asserts the historical row still exists
  afterward alongside the new one.
- Spot-check the backfilled JSON: every year/month in 2024–2026 that game8
  lists should have at least one row, and the existing passing test suite
  (`uv run pytest`) must keep passing.

## Rollout

- The backfilled `pickup_schedule.json` is loaded into SQLite only when the
  table is empty (existing `_seed_pickup_schedule` behavior). Since the
  table already has rows from the current placeholder seed, applying this
  change requires either deleting the local `wuwa_ai_coach.db` dev database
  or adding a one-off migration step so the new seed data actually loads.
  This will be spelled out as an explicit step in the implementation plan.
