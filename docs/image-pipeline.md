# Catalog image (icon) pipeline

Runbook + reference for where every catalog icon comes from, how it is stored and
served, and how to (re)fetch each kind. Kept here because the details don't all fit
in working memory.

## TL;DR

| Icon kind | Served path | On-disk file | Source | Format |
|---|---|---|---|---|
| Character | `/catalog/image/characters/<id>` | `data/catalog/icons/characters/<id>.webp` | encore live API (`api-v2.encore.moe`) — `IconRolePile` / head icon | webp |
| Weapon | `/catalog/image/weapons/<id>` | `data/catalog/icons/weapons/<id>.webp` | encore live API — weapon icon | webp |
| Echo item | `/catalog/image/echoes/<numericId>` | `data/catalog/icons/echoes/<id>.webp` | encore CDN `IconMonsterGoods160` (from datamine `phantomitem.json` `IconMiddle`) | 160×160 webp |
| Sonata set crest | `/catalog/image/echoes/s-<hash>` | `data/catalog/icons/echoes/s-<hash>.webp` | Namuwiki 데이터 스테이션 → `parse_sonata_sets` | 76×76 RGBA webp |

Note both echo *items* (`<numericId>.webp`) and sonata *set crests* (`s-<hash>.webp`)
live under the same `echoes/` kind, because the sonata id (`s-<hash>`) is stored in
`sonata_sets.json`'s `icon` field and both are served through the `echoes` kind.

## Serving (`backend/src/media.py`)

- Endpoint: `GET /catalog/image/{kind}/{id}` where `kind ∈ CATALOG_KINDS =
  ("characters", "weapons", "echoes")`.
- Resolution order (`cached_catalog_image_path`): **committed dir wins**, then the
  gitignored runtime media cache:
  1. `data/catalog/icons/{kind}/{id}.*`  ← committed, deploy-stable, no CDN dependency
  2. `media_dir()/{kind}/{id}.*`          ← gitignored runtime cache (unreleased pickup avatars, namu refreshes)
- `download_image()` is SSRF-hardened: https only, rejects private/loopback/metadata
  hosts and redirects, allow-lists image content-types, caps bytes. UA `WuWaHelper/1.0`.
- `ensure_catalog_image(kind, id, url)` caches to the **media cache** (step 2), not the
  committed dir. **Gotcha:** if a committed file already exists (even a broken
  placeholder), it wins — re-running a normal refresh will NOT replace it. To fix a
  bad committed icon you must overwrite `data/catalog/icons/{kind}/{id}.*` directly.

## Echo item icons

- Filename = the echo's numeric `id` (e.g. `60002062.webp`), matching `echoes.json`.
- Source: encore resource CDN, the `IconMonsterGoods160` variant (NOT the larger
  `IconMonsterHead732`). The asset name is on each echo's `phantomitem.json` entry in
  the datamine under `IconMiddle` → `IconMonsterGoods160/T_IconMonsterGoods160_<n>_UI`.
- URL shape: `https://api.encore.moe/resource/Data/Game/Aki/UI/UIResources/Common/Image/<folder>/<asset>.webp`
- 160×160 webp, ~8–19 KB.
- Aberration ("이상 · …") and PT2 echoes use `SG_`-prefixed / shared head assets.
- Last done: the 20 new 3.5.5 echoes (2026-07-12) — see `git log` around the echo backfill.

## Sonata set crest icons

- Filename = `s-<hash>.webp` where the id comes from `sonata_sets.json`'s `icon` field.
- Source: Namuwiki **명조: 워더링 웨이브/데이터 스테이션** page, section "4. 화음 도감".
  `src/namu/echoes.py:parse_sonata_sets(html)` returns per-set `{name_ko, two_piece,
  five_piece, icon, echo_memberships}` where `icon` is an `i.namu.wiki/...webp` URL.
- 76×76 RGBA webp, ~1.3–2.5 KB. (A blank 1326-byte file is the "not yet fetched"
  placeholder — all placeholders are byte-identical.)
- **Reproducer:** `backend/scripts/refresh_sonata_icons.py`
  - default: re-fetches only the 1326-byte placeholders
  - `--all`: refetch all 34 · `--names "A,B"`: refetch specific sets
  - downloads the Namuwiki icon, resizes to 76×76 RGBA, writes to the committed dir.
- Last done: the 3 new 3.5 sets (내려앉은 깃털의 노래 / 악을 씻어내는 마음 / 황천길을
  밝히는 등불) shipped as placeholders and were refetched 2026-07-12.

## Character / weapon icons

- Filenames = the numeric character/weapon `id` (matching `resonators.json` /
  `weapons.json`).
- Source: encore live API `https://api-v2.encore.moe/api/ko/character[/<id>]` and
  `.../weapon`. Character pile art uses `IconRolePile` (`T_IconRole_Pile_<codename>_UI`);
  head icons use the `HeadIcon` family. Gender digit in the head-icon path: **4 = male,
  5 = female** (used when disambiguating Rover variants).
- Fetching new units is an encore-live operation (not a datamine `refresh`, which is
  sealed — see the datamine-primary migration notes). Download to the committed dir.

## When to (re)fetch

- **New echoes added** → fetch their `IconMonsterGoods160` from encore into
  `icons/echoes/<id>.webp`.
- **New sonata set added** → `refresh_sonata_icons.py` (Namuwiki).
- **New character/weapon added** → encore live API pile/icon into the committed dir.
- **Icon shows blank/broken on the site** → check the committed file size; a 1326-byte
  sonata icon is the placeholder. Overwrite the committed file (media-cache refresh
  won't take effect while a committed file exists).

## No restart needed

Image files are read from disk per request (`cached_catalog_image_path`), so newly
written/overwritten icons serve immediately — no backend restart. (The JSON *catalog*
is `@lru_cache`d and does need a restart; icons do not.)
