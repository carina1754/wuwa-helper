# Namuwiki WuWa Data Platform — Design

## Problem / Goal

Build a durable, comprehensive Wuthering Waves (명조) game-data store, sourced by
crawling **Namuwiki** (namu.wiki), stored in our PostgreSQL, and used by:
1. The **pickup schedule** (픽업 일정표) redesign — show each banner's featured
   characters AND weapons, with a character/weapon filter toggle, and images
   served from our own local cache.
2. A **future AI recommendation/build system** — needs full character kit data:
   skills + damage multipliers, resonance chains (공명 사슬 / 1·2·3돌), stats,
   ascension, recommended weapons/echoes/teams.

Namuwiki is chosen because it is stable (won't disappear like hakush.in, which
shut down), Korean-native (matches this app's UI), and comprehensive. Because
all data is **stored in our own DB and all images cached locally**, a future
Namuwiki outage/layout-change only affects fetching *new* content, never the
already-stored data.

## Feasibility (verified)

- Namuwiki is crawlable with a browser User-Agent (curl → HTTP 200, full
  server-rendered HTML; `i.namu.wiki/i/{hash}` images fetch as real bytes).
- Character page (e.g. `로코코(명조: 워더링 웨이브)`, ~2 MB, 104 tables) has clear
  section headings: `3.1 속성`(stats) / `3.1.1 공명자 돌파`(ascension) /
  `3.2 스킬`(basic/skill/circuit/liberation/intro/outro/stagger, with ~10k
  multiplier `%` tokens) / `3.3 공명 체인`(resonance chain S0-S6) /
  `6 운영`(recommended teams / weapons 5★·4★ / echoes) / `7 평가`.
- Weapon lists exist per type: `무기/{권갑,권총,대검,증폭기,직검}`.
- Banner history exists: `튜닝/{캐릭터,무기} 이벤트 튜닝` (per-version character &
  weapon banners with dates) and `일정`.
- Character pages are at `/w/{name}(명조: 워더링 웨이브)` (36+ found via the
  `공명자` list). Names are Korean.

**Caveat (accepted):** Namuwiki HTML is large and noisy (ads, nav, no image
`alt` text, deeply nested tables). Parsing must be section-heading-driven and
per-page-type, using a real HTML parser (add `beautifulsoup4` via `uv add`).
Some fields extract cleanly (headings, tables, images); some prose/build advice
is semi-structured and stored as-is. The scraper is inherently
layout-dependent and will need occasional maintenance — mitigated by storing
everything in our DB so breakage never loses existing data.

## Data model (PostgreSQL; document-in-`data_json` pattern, like existing tables)

New/${extended} tables (each `id`/key columns + a `data_json` blob validated by
a Pydantic model, matching the existing `character_catalog`/`game_updates`
convention):

- `character_catalog` (EXTEND existing): add rich fields — `skills` (per skill:
  name, type, description, damage multipliers by level), `resonance_chain`
  (S1–S6 name/effect), `ascension`/`stats`, `recommended_weapons`,
  `recommended_echoes` (main echo, sonata set combo, main/sub-stat priority,
  echo optimize), `recommended_teams` (each: teammates + roles + synergy notes,
  from 6.1 추천 파티 / 임의 파티), `pros_cons`, plus Korean/English name linkage.
  Keep existing `image`/`splash_image` (now locally cached).
- `weapon_catalog` (NEW): `name_ko`, `name_en?`, `rarity`, `weapon_type`,
  `icon` (local cached path), `stats`/`passive`, `source`.
- `echo_catalog` (NEW): FULL echo coverage —
  - `sonata_sets` (소나타/화음 이펙트): set name, 2-piece and 5-piece effects,
    icon, element affinity.
  - `echoes` (개별 에코): name, cost (1/3/4), sonata membership, active/echo
    skill, class (calamity/overlord/elite/common), icon.
  - main-stat / sub-stat option tables per cost.
  Sourced from the Namuwiki echo page(s) + character pages' 6.3 sections.
- `pickup_schedule` (EXTEND): add `weapons: list[str]` alongside `characters`;
  populate from Namuwiki banner-history crawl.
- `namu_cache`/`refresh_state` (NEW/reuse): track per-page fetch time + raw
  snapshot for durability and incremental refresh.

Pydantic models mirror these in `backend/src/models.py`; TS types in
`frontend/src/lib/types.ts` for the fields the UI consumes.

## Architecture

### Crawl layer (`backend/src/namu/…`)
- `namu_client.py`: fetch a Namuwiki page (browser UA, timeout, retry, the same
  SSRF-safe download path as `media.py` for images), cache raw HTML+snapshot in
  DB, respect polite rate limits.
- Per-page-type parsers (BeautifulSoup): `parse_character.py`,
  `parse_weapon_list.py`, `parse_banner_history.py`. Each returns validated
  model dicts. Parsers are section-heading-driven and defensive (missing
  section → field omitted, never a crash).
- Orchestrator + refresh worker: iterate the character/weapon/banner index
  pages, fetch+parse+upsert into the DB, on a schedule (like the existing
  daily `content_refresh` worker). Incremental: only re-fetch changed/new pages.

### Local image cache (generalize `media.py`)
- Extend the existing hardened `media.py` to cache catalog images by
  `(kind, id)`: character avatars/splash, weapon icons, echo icons. Stored
  under `backend/media/{characters,weapons,echoes}/` (git-ignored). Served by
  routes `GET /catalog/image/{kind}/{id}` (404 + traversal-guarded, reusing the
  update-image pattern). Catalog APIs return local served paths, not external
  URLs. A refresh step downloads images once via the SSRF-safe `download_image`.

### API + consumers
- `GET /weapons`, extended `GET /characters`, extended `GET /pickup-schedule`.
- Frontend: pickup schedule redesign (remove the 12-month grid + stat cards;
  add a character/weapon filter toggle; render character avatars + weapon icons
  from the local cache). `CharacterPlanner` switches to locally-cached images.
- Future AI system reads the rich `character_catalog`/`weapon_catalog` data.

## Curated vs. crawled (per prior user decisions)
- **Pickup/banner schedule**: crawled from Namuwiki tuning pages (auto-refresh).
- **Weapon catalog**: the user chose a *curated* module for the weapon list —
  reconciled here as: crawl the Namuwiki weapon pages once to *generate* a
  committed `curated_weapons` seed, which is then maintained in-repo and applied
  to `weapon_catalog` (durable, like `curated_updates`). New weapons added per
  version.
- **Character rich data**: crawled from Namuwiki character pages, stored in DB.

## Phasing (build order — each phase ships independently)

1. **P1 — Crawl+cache foundation:** `namu_client` + `media.py` generalization +
   `GET /catalog/image/{kind}/{id}` + `beautifulsoup4` dep. Deliverable: can
   fetch a Namuwiki page and cache an image locally, tested.
2. **P2 — Weapon catalog:** `parse_weapon_list` over the 5 type pages →
   `weapon_catalog` + curated seed + `/weapons` API + cached icons.
3. **P3 — Pickup schedule + weapons:** `parse_banner_history` (튜닝 pages) →
   `pickup_schedule.weapons`; frontend redesign (filter toggle, remove month
   grid, char+weapon icons, local images) + `CharacterPlanner` local images.
   Korean↔English character-name alias map for avatar linkage.
4. **P4 — Character rich data:** `parse_character` over all character pages →
   extended `character_catalog` (skills+multipliers, resonance chain, stats,
   ascension, `recommended_weapons`/`recommended_echoes`/`recommended_teams`,
   pros/cons). This captures the per-character **build & team-combo** info.
   Foundation for the AI system.
5. **P5 — Echo catalog + refresh automation:** `parse_echoes` → full
   `echo_catalog` (sonata sets with 2/5-piece effects, individual echoes with
   cost/skill/class, main/sub-stat tables); plus the scheduled incremental
   refresh worker for characters/weapons/echoes/banners.

Each phase is spec'd into a task plan and built task-by-task (TDD, reviewed).
P1–P3 deliver the user-visible pickup feature; P4–P5 stock the AI data.

## Risks / mitigations
- **Parser brittleness** → per-page-type, heading-driven, defensive parsers;
  raw snapshots stored; DB retains data across breakage; unit tests on saved
  sample HTML fixtures (committed under tests, not the full pages).
- **Korean↔English character matching** (Namuwiki KO vs `character_catalog` EN)
  → maintained alias map; unmatched names logged, never crash.
- **Rate limiting / politeness** → throttle, cache raw HTML, incremental refresh.
- **Dev isolation** → all crawling/writes go to `wuwa_ai_coach_dev` in dev
  (conftest already forces tests off prod); images to a temp `MEDIA_DIR` in
  tests.

## Out of scope (for now)
- The AI recommendation logic itself (P4/P5 only *store* the data it will need).
- Full prose/lore extraction (store character bio/eval as text, not modeled).
