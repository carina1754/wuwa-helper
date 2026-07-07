# wuthering.gg Data Pipeline — Design Spec

**Date:** 2026-07-07
**Status:** Draft (awaiting user review)
**Phase:** 1 of 2. This spec covers the **data pipeline only**. The party-builder
planner UI (Phase 2) gets its own spec/plan cycle once this data lands.

## Goal

Extract wuthering.gg's complete Wuthering Waves dataset — characters, weapons,
echoes, sonata sets, and the supporting lookup tables — into our PostgreSQL DB,
with **Korean** text and **locally-cached images**, keyed by the game's numeric
IDs (which already match our `character_catalog` IDs). This replaces our thin
Namuwiki-derived data with a complete, structured dataset for the encyclopedia
and the party builder.

## Why this source (decided during brainstorming)

- Namuwiki data is incomplete (weapons had no stats/passives; only 27/56 char
  kits; some garbage-parsed pages).
- wuthering.gg's data is **not** behind a scrapeable API. Verified: fresh page
  loads of `/ko/weapons` and `/ko/characters/carlotta` make **zero** data
  requests — every field renders from **static JS chunks** (SSG). `api.wuthering.gg`
  is a Flask service used only for social features (comments, bookmarks).
- So the data is downloadable static content: no auth, no Cloudflare bot-block
  on assets, and durable once copied into our DB.

## Data source & format (confirmed)

- Each UI language ships a **single data chunk** at `https://wuthering.gg/_nuxt/<hash>.js`
  (~1.5–1.6 MB) containing the *entire* dataset in that language. The **Korean**
  chunk was `Bl-Led-z.js` in the inspected build (contains `카멜리아`).
- **The hash changes per deploy**, so the pipeline must locate the current KO
  data chunk dynamically (see Discovery).
- Data is embedded as **valid JSON** (double-quoted keys). Character sample
  (Camellya, `Id` 1603 — matches our `cat-1603`):

  ```json
  {"Id":1603,"QualityId":5,"RoleType":1,"ElementId":6,"WeaponType":2,
   "RoleHeadIconBig":"T_IconRoleHead150_29_UI.png",
   "FormationRoleCard":"T_IconRole_Pile_chun_UI.png",
   "Ascension":[{"MaxLevel":40,"Consume":[{"Value":4,"Item":{"Name":"저주파수 의음 성핵","Icon":"T_IconMout_O_002_1_UI.png"}}, ...]}, ...],
   "Skills":[...],"ResonantChainGroup":[{"NodeName":"...","NodeIcon":"...","GroupIndex":n}, ...], ... }
  ```

- **ID→name enums** (`ElementId`, `WeaponType`, `RoleType`, `QualityId`) resolve
  via lookup tables also embedded in the chunk, with a curated fallback map:
  - Element: 1 Glacio(응결) · 2 Fusion(열용융) · 3 Electro(전도) · 4 Aero(기류) · 5 Spectro(회절) · 6 Havoc(인멸)
  - WeaponType: 1 Broadsword(대검) · 2 Sword(직검) · 3 Pistols(권총) · 4 Gauntlets(권갑) · 5 Rectifier(증폭기)
  - (Camellya `ElementId:6`→Havoc, `WeaponType:2`→Sword — both verified correct.)
- **Images**: asset filenames map to `https://wuthering.gg/images/<category>/<AssetName>`.
  Observed categories from the frontend: `iconrolehead150/`, `iconelement/`,
  `icondevice/` (chain nodes), plus weapon/echo/skill icon paths. The pipeline
  derives the category per field.

## Architecture

Four stages, all in a new backend module `src/wutheringgg/` (kept separate from
the Namuwiki code in `src/namu/`):

1. **Discovery** — `find_ko_data_chunk() -> (url, text)`
   - Fetch `https://wuthering.gg/ko/characters` (browser UA), enumerate
     `/_nuxt/*.js` chunk hashes referenced by the entry bundle + build manifest.
   - Fetch candidates and pick the KO data chunk by **content signature**: a
     known Korean resonator name (e.g. `카멜리아`) **and** the data key
     `"QualityId"`/`"ElementId"`. Fail loudly if none matches (build changed).

2. **Extraction** — `extract_dataset(text) -> dict[str, list[dict]]`
   - The dataset lives as JS variable assignments of JSON arrays. Locate each by
     a **key signature** (e.g. the first `{"Id":...,"QualityId":...,"WeaponType":...}`
     for characters) and **balanced-bracket scan** outward to the enclosing
     array, then `json.loads`. Repeat for weapons, echoes/phantoms, sonata sets,
     and lookup tables.
   - Returns raw record lists per entity type. No network, pure function → unit
     testable against a saved fixture chunk.

3. **Normalization + image caching** — per entity type
   - Map enum IDs → names (Korean + English), normalize to our schema, join by
     `Id`. Collect every image asset referenced, download via the SSRF-hardened
     `download_image`, cache under our media dir, and rewrite fields to local
     `/catalog/image/...` paths (reuse `ensure_catalog_image`).

4. **Storage** — upsert into DB
   - Extend existing tables where they align (`character_catalog`,
     `weapon_catalog`, `echo_catalog`, `sonata_set`) and add rich detail as the
     `data_json` blob; add new tables only where an entity has no home
     (e.g. `character_detail` for skills/chains/ascension if kept separate from
     the catalog row). Keyed by game `Id`.

## Storage decisions

- **Characters**: keep `character_catalog` (56 rows, already keyed by game Id) as
  the spine; **replace** its `data_json` with the wuthering.gg-sourced record
  (element/weapon/rarity/role/images + skills, resonance chains, ascension,
  stats, recommended builds). Existing consumers (planner, pickup `catalog_id`
  join) keep working because the Id and the `image`/`name` fields are preserved.
- **Weapons**: enrich `weapon_catalog` rows with stats + passive + level curve.
- **Echoes / sonata**: enrich `echo_catalog` / `sonata_set` with full stats/skills.
- All image URLs stored as local `/catalog/image/...` paths.

## Parallelization plan (Workflow)

The user asked to parallelize via the Workflow tool. Shape:

- **Phase A — Discover (1 agent)**: locate the KO data chunk, save it to the
  scratchpad, and report its path + the top-level array signatures it found.
- **Phase B — Extract+normalize (parallel, one agent per entity type)**:
  characters · weapons · echoes+sonata · lookup-tables. Each reads the saved
  chunk, extracts and normalizes its slice, returns structured records +
  the list of image assets it needs.
- **Phase C — Image manifest (barrier)**: dedupe the union of image assets
  across entity types (avoids re-downloading shared icons), then cache them in
  parallel batches.
- **Phase D — Load + verify (1 agent)**: upsert to DB, then verify counts and
  spot-check (e.g. Camellya has Havoc/Sword/5★ + non-empty skills + chains, all
  images resolve locally).

Extraction stays **deterministic Python** (a committed parser module); the
workflow parallelizes the *entity slices* and *image batches*, not the parsing
logic itself. The parser is the durable artifact; the workflow is the one-time
runner.

## Scope

**In scope (Phase 1):** the extraction pipeline + normalized data + cached
images in the DB; backend module + parser tests; a refresh entrypoint.

**Out of scope (later phases):** the party-builder UI, the encyclopedia UI,
exposing new API fields to the frontend, and any wuthering.gg *editorial*
content (tier ratings, prose build guides) beyond the structured game data.

## Risks & mitigations

- **Build-hash churn** → Discovery locates the chunk by content signature, not a
  pinned hash; fails loudly with a clear message when the build format changes.
- **Minified-JS parsing fragility** → parse by JSON key-signature + balanced
  brackets against a saved fixture; unit-test the parser on the fixture so a
  site change surfaces as a test failure, not silent bad data.
- **Enum/image drift** → keep the curated enum map small and assert every
  referenced enum resolves; log any unmapped enum or missing image.
- **Isolation** → all work uses the `wuwa_ai_coach_dev` DB and a fixture-first
  parser; no writes to prod data.

## Testing

- Parser unit tests against a saved fixture chunk (characters/weapons/echoes
  each parse to the expected count and a golden sample record).
- Enum-resolution tests (every `ElementId`/`WeaponType` maps).
- Image-path derivation tests (asset name → correct category URL).
- Post-load DB verification (counts + Camellya golden spot-check).
