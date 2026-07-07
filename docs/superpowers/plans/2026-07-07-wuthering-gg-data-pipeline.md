# wuthering.gg Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract wuthering.gg's bundled static dataset (characters, weapons, echoes, sonata sets) into our Postgres DB with Korean text and locally-cached images, keyed by the game's numeric IDs.

**Architecture:** A new `backend/src/wutheringgg/` module: `client.py` locates + downloads the per-entity KO data chunks from `wuthering.gg/_nuxt/*.js`; `extract.py` pulls each embedded JSON array via anchor + string-aware balanced-bracket scan; `normalize.py` maps enum IDs → names and derives image URLs; `refresh.py` orchestrates discovery → extract → normalize → image-cache → DB upsert. The parser is deterministic and unit-tested against committed fixtures; a Workflow parallelizes the one-time run's image downloads.

**Tech Stack:** Python 3.12, psycopg (Postgres), `urllib`/existing `download_image`, pytest. Frontend untouched in this phase.

## Global Constraints

- Dev DB only: all runs and tests use `wuwa_ai_coach_dev` (conftest forces it). Never write prod.
- Reuse existing media infra: `src/media.py` `download_image(source_url, dest_stem)` and `ensure_catalog_image(kind, item_id, source_url)`; image serving route `/catalog/image/{kind}/{item_id}` already exists. Do not reinvent.
- Keep `character_catalog` keyed by the game numeric `Id` (e.g. Camellya=1603). Preserve each row's `id`, `name`, and a local `image` path so existing consumers (planner, pickup `catalog_id` join) keep working.
- Image base: `https://wuthering.gg/images/<category>/<AssetName>`. Asset names look like `T_IconRoleHead150_29_UI.png`.
- Data chunk hashes change per deploy — never pin a hash; locate chunks by content signature and fail loudly when no chunk matches.
- Element enum (verified): `{1:Glacio, 2:Fusion, 3:Electro, 4:Aero, 5:Spectro, 6:Havoc}`. WeaponType enum (verified): `{1:Broadsword/대검, 2:Sword/직검, 3:Pistols/권총, 4:Gauntlets/권갑, 5:Rectifier/증폭기}`. Character records also carry a localized `Element` name field — prefer it for the element name; map `WeaponType` via the enum.

---

### Task 1: Balanced-bracket array extractor

**Files:**
- Create: `backend/src/wutheringgg/__init__.py` (empty)
- Create: `backend/src/wutheringgg/extract.py`
- Test: `backend/tests/test_wutheringgg_extract.py`

**Interfaces:**
- Produces: `extract_array(text: str, anchor: str) -> list[dict]` — finds `anchor` in `text`, expands to the enclosing `[...]`, returns `json.loads` of it. Raises `ValueError` if the anchor is missing.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_wutheringgg_extract.py
import pytest
from src.wutheringgg.extract import extract_array

def test_extract_array_pulls_enclosing_array():
    text = 'var x=[{"Id":1,"Name":"a"},{"Id":2,"Name":"b[racket]"}];foo'
    arr = extract_array(text, '"Id":2')
    assert arr == [{"Id": 1, "Name": "a"}, {"Id": 2, "Name": "b[racket]"}]

def test_extract_array_ignores_brackets_inside_strings():
    text = '[{"k":"]["},{"k":"x"}]'
    arr = extract_array(text, '"k":"x"')
    assert len(arr) == 2 and arr[0]["k"] == "]["

def test_extract_array_raises_when_anchor_missing():
    with pytest.raises(ValueError):
        extract_array("[]", "nope")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_wutheringgg_extract.py -q`
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/wutheringgg/extract.py
"""Extract embedded JSON arrays from wuthering.gg's minified Nuxt data chunks."""
from __future__ import annotations

import json


def extract_array(text: str, anchor: str) -> list[dict]:
    """Locate `anchor` in `text`, expand to the enclosing JSON array, and parse it."""
    a = text.find(anchor)
    if a < 0:
        raise ValueError(f"anchor not found: {anchor!r}")
    # Walk backward to the array's opening '[' (bracket-balanced).
    bal = 0
    i = a
    while i >= 0:
        c = text[i]
        if c == "]":
            bal += 1
        elif c == "[":
            if bal == 0:
                break
            bal -= 1
        i -= 1
    if i < 0:
        raise ValueError("no enclosing array start found")
    start = i
    # Forward, string-aware, to the matching ']'.
    depth = 0
    j = start
    in_str = False
    esc = False
    while j < len(text):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start : j + 1])
        j += 1
    raise ValueError("unterminated array")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_wutheringgg_extract.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/wutheringgg/__init__.py backend/src/wutheringgg/extract.py backend/tests/test_wutheringgg_extract.py
git commit -m "feat: balanced-bracket JSON array extractor for wuthering.gg chunks"
```

---

### Task 2: Entity parsers over a committed fixture

**Files:**
- Modify: `backend/src/wutheringgg/extract.py` (add `parse_characters`, `parse_weapons`, `parse_echoes`)
- Create: `backend/tests/fixtures/wuwagg_characters_ko.js` (a real 2-character slice — see Step 1)
- Test: `backend/tests/test_wutheringgg_extract.py` (add cases)

**Interfaces:**
- Consumes: `extract_array` from Task 1.
- Produces:
  - `parse_characters(text: str) -> list[dict]` — anchors on `'"ResonantChainGroup"'`, returns the character array.
  - `parse_weapons(text: str) -> list[dict]` — anchors on the weapon signature (see below).
  - `parse_echoes(text: str) -> list[dict]` — anchors on the echo signature (see below).

- [ ] **Step 1: Create the fixture**

Save two real character objects (Korean) as a JS-array fixture. Generate it from a live chunk once, then commit the trimmed file. Fixture content shape (abbreviated — keep the full two objects when generating):

```javascript
var C=[{"Id":1102,"Name":"산화","NameEn":"Sanhua","QualityId":4,"ElementId":1,"Element":"응결","WeaponType":2,"RoleType":2,"RoleHeadIconBig":"T_IconRoleHead150_5_UI.png","Skills":[{"Name":"..."}],"ResonantChainGroup":[{"NodeName":"...","NodeIcon":"...","GroupIndex":1}],"Ascension":[],"Stats":{}},{"Id":1603,"Name":"카멜리아","NameEn":"Camellya","QualityId":5,"ElementId":6,"Element":"인멸","WeaponType":2,"RoleType":1,"RoleHeadIconBig":"T_IconRoleHead150_29_UI.png","Skills":[],"ResonantChainGroup":[],"Ascension":[],"Stats":{}}]
```

To generate it for real: fetch the current KO characters chunk (Task 3's `client.find_data_chunk("characters")`), `parse_characters`, keep the objects with `Id in (1102, 1603)`, and `json.dumps` them into `var C=[...]`.

- [ ] **Step 2: Write the failing test**

```python
from pathlib import Path
from src.wutheringgg.extract import parse_characters

FIX = Path(__file__).parent / "fixtures" / "wuwagg_characters_ko.js"

def test_parse_characters_from_fixture():
    text = FIX.read_text(encoding="utf-8")
    chars = parse_characters(text)
    by_id = {c["Id"]: c for c in chars}
    assert 1603 in by_id
    assert by_id[1603]["Name"] == "카멜리아"
    assert by_id[1603]["NameEn"] == "Camellya"
    assert by_id[1603]["QualityId"] == 5
    assert by_id[1603]["WeaponType"] == 2
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_wutheringgg_extract.py::test_parse_characters_from_fixture -q`
Expected: FAIL (`parse_characters` not defined)

- [ ] **Step 4: Implement the parsers**

```python
# append to backend/src/wutheringgg/extract.py

# Content signatures that identify each entity's data array within its chunk.
CHARACTER_ANCHOR = '"ResonantChainGroup"'
WEAPON_ANCHOR = '"WeaponType":'      # weapon objects also carry stat + skill fields
ECHO_ANCHOR = '"Cost"'                # phantom/echo objects carry Cost + Sonata

def parse_characters(text: str) -> list[dict]:
    return extract_array(text, CHARACTER_ANCHOR)

def parse_weapons(text: str) -> list[dict]:
    return extract_array(text, WEAPON_ANCHOR)

def parse_echoes(text: str) -> list[dict]:
    return extract_array(text, ECHO_ANCHOR)
```

Note: `parse_weapons`/`parse_echoes` anchors are confirmed against the live weapon/echo chunks during Task 3 discovery; if a live chunk's first matching object is not the entity array, tighten the anchor to a more specific key sequence found in that chunk and update the fixture-backed test accordingly.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_wutheringgg_extract.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/wutheringgg/extract.py backend/tests/fixtures/wuwagg_characters_ko.js backend/tests/test_wutheringgg_extract.py
git commit -m "feat: character/weapon/echo array parsers with committed fixture"
```

---

### Task 3: Chunk discovery client

**Files:**
- Create: `backend/src/wutheringgg/client.py`
- Test: `backend/tests/test_wutheringgg_client.py`

**Interfaces:**
- Consumes: `parse_characters`/`parse_weapons`/`parse_echoes` from Task 2.
- Produces:
  - `fetch_chunk_names() -> list[str]` — GET `https://wuthering.gg/ko/characters` with a browser UA, return every `/_nuxt/<hash>.js` referenced (regex `[A-Za-z0-9_-]{8}\.js`), plus those referenced by the entry bundle.
  - `download_chunk(name: str) -> str` — GET `https://wuthering.gg/_nuxt/<name>` text.
  - `find_data_chunk(kind: str) -> str` — download candidate chunks, return the text of the one whose content matches `kind`'s signature. `kind` ∈ `{"characters","weapons","echoes"}`. Signatures: characters → contains `카멜리아` and `"ResonantChainGroup"`; weapons → contains `"WeaponType":` and a known weapon KO name passed via `_SIGNATURE`; echoes → contains `"Cost"` and a known echo KO name. Raise `RuntimeError("data chunk not found for {kind}; site build may have changed")` if none match.

- [ ] **Step 1: Write the failing test** (network-free, monkeypatched)

```python
# backend/tests/test_wutheringgg_client.py
from src.wutheringgg import client

def test_find_data_chunk_picks_by_signature(monkeypatch):
    monkeypatch.setattr(client, "fetch_chunk_names", lambda: ["a.js", "b.js"])
    blobs = {
        "a.js": 'unrelated code',
        "b.js": 'x=[{"Id":1603,"Name":"카멜리아","ResonantChainGroup":[]}]',
    }
    monkeypatch.setattr(client, "download_chunk", lambda n: blobs[n])
    text = client.find_data_chunk("characters")
    assert "카멜리아" in text

def test_find_data_chunk_raises_when_absent(monkeypatch):
    monkeypatch.setattr(client, "fetch_chunk_names", lambda: ["a.js"])
    monkeypatch.setattr(client, "download_chunk", lambda n: "nothing here")
    import pytest
    with pytest.raises(RuntimeError):
        client.find_data_chunk("characters")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_wutheringgg_client.py -q`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement the client**

```python
# backend/src/wutheringgg/client.py
"""Fetch and locate wuthering.gg's static Nuxt data chunks."""
from __future__ import annotations

import re
import urllib.request

BASE = "https://wuthering.gg"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
_CHUNK_RE = re.compile(r"[A-Za-z0-9_-]{8}\.js")

# Signature strings that must appear in each entity's data chunk.
_SIGNATURES = {
    "characters": ["카멜리아", '"ResonantChainGroup"'],
    "weapons": ['"WeaponType":', "스펙트럴 트리거"],
    "echoes": ['"Cost"', "타종 거북이"],
}


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (fixed host)
        return resp.read().decode("utf-8", "replace")


def fetch_chunk_names() -> list[str]:
    html = _get(f"{BASE}/ko/characters")
    entry = re.search(r'/_nuxt/([A-Za-z0-9_-]{8}\.js)', html)
    names = set(_CHUNK_RE.findall(html))
    if entry:
        names.update(_CHUNK_RE.findall(_get(f"{BASE}/_nuxt/{entry.group(1)}")))
    return sorted(names)


def download_chunk(name: str) -> str:
    return _get(f"{BASE}/_nuxt/{name}")


def find_data_chunk(kind: str) -> str:
    sig = _SIGNATURES[kind]
    for name in fetch_chunk_names():
        try:
            text = download_chunk(name)
        except Exception:
            continue
        if all(s in text for s in sig):
            return text
    raise RuntimeError(f"data chunk not found for {kind}; site build may have changed")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_wutheringgg_client.py -q`
Expected: PASS

- [ ] **Step 5: Live smoke check (manual, not a committed test)**

Run: `cd backend && uv run python -c "from src.wutheringgg import client, extract; t=client.find_data_chunk('characters'); print('chars', len(extract.parse_characters(t)))"`
Expected: prints `chars 53` (± as roster grows). If weapons/echoes anchors mismatch, adjust `extract.WEAPON_ANCHOR`/`ECHO_ANCHOR` and the `_SIGNATURES` here, then re-run.

- [ ] **Step 6: Commit**

```bash
git add backend/src/wutheringgg/client.py backend/tests/test_wutheringgg_client.py
git commit -m "feat: wuthering.gg chunk discovery by content signature"
```

---

### Task 4: Normalization (enum maps + image URLs)

**Files:**
- Create: `backend/src/wutheringgg/normalize.py`
- Test: `backend/tests/test_wutheringgg_normalize.py`

**Interfaces:**
- Produces:
  - `WEAPON_TYPE: dict[int, tuple[str, str]]` — id → (english, korean).
  - `image_url(category: str, asset: str) -> str` — `https://wuthering.gg/images/{category}/{asset}`.
  - `normalize_character(raw: dict) -> dict` — returns `{id, name, name_en, rarity, element, weapon_type, weapon_type_ko, role_type, head_icon_asset, skills, resonance_chain, ascension, stats, introduction}`. Image fields hold raw asset names (Task 5 caches + rewrites them).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_wutheringgg_normalize.py
from src.wutheringgg.normalize import normalize_character, image_url, WEAPON_TYPE

RAW = {
    "Id": 1603, "Name": "카멜리아", "NameEn": "Camellya", "QualityId": 5,
    "ElementId": 6, "Element": "인멸", "WeaponType": 2, "RoleType": 1,
    "RoleHeadIconBig": "T_IconRoleHead150_29_UI.png",
    "Skills": [{"Name": "s"}], "ResonantChainGroup": [{"NodeName": "n"}],
    "Ascension": [], "Stats": {"atk": 1}, "Introduction": "hi",
}

def test_normalize_character():
    c = normalize_character(RAW)
    assert c["id"] == 1603
    assert c["name"] == "카멜리아"
    assert c["name_en"] == "Camellya"
    assert c["rarity"] == 5
    assert c["element"] == "인멸"
    assert c["weapon_type"] == "Sword"
    assert c["weapon_type_ko"] == "직검"
    assert c["head_icon_asset"] == "T_IconRoleHead150_29_UI.png"
    assert len(c["skills"]) == 1 and len(c["resonance_chain"]) == 1

def test_image_url():
    assert image_url("iconrolehead150", "T_x.png") == "https://wuthering.gg/images/iconrolehead150/T_x.png"

def test_weapon_type_complete():
    assert set(WEAPON_TYPE) == {1, 2, 3, 4, 5}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_wutheringgg_normalize.py -q`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement**

```python
# backend/src/wutheringgg/normalize.py
"""Normalize raw wuthering.gg records into our schema; derive image URLs."""
from __future__ import annotations

WEAPON_TYPE: dict[int, tuple[str, str]] = {
    1: ("Broadsword", "대검"),
    2: ("Sword", "직검"),
    3: ("Pistols", "권총"),
    4: ("Gauntlets", "권갑"),
    5: ("Rectifier", "증폭기"),
}


def image_url(category: str, asset: str) -> str:
    return f"https://wuthering.gg/images/{category}/{asset}"


def normalize_character(raw: dict) -> dict:
    wt = WEAPON_TYPE.get(raw.get("WeaponType"), ("", ""))
    return {
        "id": raw["Id"],
        "name": raw.get("Name"),
        "name_en": raw.get("NameEn"),
        "rarity": raw.get("QualityId"),
        "element": raw.get("Element"),
        "weapon_type": wt[0],
        "weapon_type_ko": wt[1],
        "role_type": raw.get("RoleType"),
        "head_icon_asset": raw.get("RoleHeadIconBig"),
        "skills": raw.get("Skills") or [],
        "resonance_chain": raw.get("ResonantChainGroup") or [],
        "ascension": raw.get("Ascension") or [],
        "stats": raw.get("Stats") or {},
        "introduction": raw.get("Introduction"),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_wutheringgg_normalize.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/wutheringgg/normalize.py backend/tests/test_wutheringgg_normalize.py
git commit -m "feat: normalize wuthering.gg records + image URL derivation"
```

---

### Task 5: Image asset caching

**Files:**
- Modify: `backend/src/media.py` — confirm `ensure_catalog_image` accepts an absolute source URL and a kind; if `characters` kind already exists, reuse. Add kind `"skills"` and `"nodes"` to `CATALOG_KINDS` if missing.
- Create: `backend/src/wutheringgg/images.py`
- Test: `backend/tests/test_wutheringgg_images.py`

**Interfaces:**
- Consumes: `image_url` (Task 4), `ensure_catalog_image(kind, item_id, source_url)` (media.py).
- Produces: `cache_asset(kind: str, category: str, asset: str) -> str | None` — derives the source URL, caches via `ensure_catalog_image`, returns the local `/catalog/image/...` path (or `None` on failure). `item_id` is the asset filename without extension.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_wutheringgg_images.py
from src.wutheringgg import images

def test_cache_asset_uses_image_url_and_returns_local(monkeypatch):
    seen = {}
    def fake_ensure(kind, item_id, src):
        seen.update(kind=kind, item_id=item_id, src=src)
        return f"/catalog/image/{kind}/{item_id}"
    monkeypatch.setattr(images, "ensure_catalog_image", fake_ensure)
    out = images.cache_asset("characters", "iconrolehead150", "T_IconRoleHead150_29_UI.png")
    assert out == "/catalog/image/characters/T_IconRoleHead150_29_UI"
    assert seen["src"] == "https://wuthering.gg/images/iconrolehead150/T_IconRoleHead150_29_UI.png"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_wutheringgg_images.py -q`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement**

```python
# backend/src/wutheringgg/images.py
"""Cache wuthering.gg image assets locally via the existing media infra."""
from __future__ import annotations

import os

from src.media import ensure_catalog_image
from src.wutheringgg.normalize import image_url


def cache_asset(kind: str, category: str, asset: str) -> str | None:
    if not asset:
        return None
    item_id = os.path.splitext(asset)[0]
    return ensure_catalog_image(kind, item_id, image_url(category, asset))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_wutheringgg_images.py -q`
Expected: PASS

- [ ] **Step 5: Confirm media kinds** — open `backend/src/media.py`, ensure `CATALOG_KINDS` includes `"characters"` (it does) and add `"skills"`, `"nodes"` if the plan later caches skill/chain-node icons. Add a one-line test in `tests/test_media.py` mirroring an existing kind test for any new kind.

- [ ] **Step 6: Commit**

```bash
git add backend/src/wutheringgg/images.py backend/tests/test_wutheringgg_images.py backend/src/media.py
git commit -m "feat: cache wuthering.gg image assets via media infra"
```

---

### Task 6: DB upsert + refresh orchestration

**Files:**
- Create: `backend/src/wutheringgg/refresh.py`
- Modify: `backend/src/database.py` — ensure `character_catalog` exists (it does); no schema change if we only rewrite `data_json`.
- Test: `backend/tests/test_wutheringgg_refresh.py`

**Interfaces:**
- Consumes: `client.find_data_chunk`, `extract.parse_characters`, `normalize_character`, `images.cache_asset`.
- Produces: `refresh_characters(*, fetch=client.find_data_chunk, cache=images.cache_asset) -> int` — discover → parse → normalize → cache head image → upsert each character into `character_catalog` (`id`, `name`, `role`, `data_json`), preserving existing `role` when the row already exists. Returns the count. `fetch`/`cache` are injected for tests.

- [ ] **Step 1: Write the failing test** (no network, no real images)

```python
# backend/tests/test_wutheringgg_refresh.py
import json
from src.wutheringgg import refresh
from src.database import get_connection, init_db

def test_refresh_characters_upserts(monkeypatch):
    init_db()
    fixture = '[{"Id":1603,"Name":"카멜리아","NameEn":"Camellya","QualityId":5,"ElementId":6,"Element":"인멸","WeaponType":2,"RoleType":1,"RoleHeadIconBig":"T_x.png","Skills":[],"ResonantChainGroup":[],"Ascension":[],"Stats":{}}]'
    with get_connection() as c:
        c.execute("DELETE FROM character_catalog WHERE id=%s", (1603,)); c.commit()
    n = refresh.refresh_characters(
        fetch=lambda kind: fixture,
        cache=lambda kind, cat, asset: f"/catalog/image/{kind}/x",
    )
    assert n == 1
    with get_connection() as c:
        row = c.execute("SELECT data_json FROM character_catalog WHERE id=%s", (1603,)).fetchone()
    d = json.loads(row["data_json"])
    assert d["name"] == "카멜리아" and d["weapon_type"] == "Sword"
    assert d["image"] == "/catalog/image/characters/x"
    with get_connection() as c:
        c.execute("DELETE FROM character_catalog WHERE id=%s", (1603,)); c.commit()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_wutheringgg_refresh.py -q`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement**

```python
# backend/src/wutheringgg/refresh.py
"""Orchestrate the wuthering.gg character refresh into character_catalog."""
from __future__ import annotations

import json

from src.database import get_connection
from src.wutheringgg import client, extract, images
from src.wutheringgg.normalize import normalize_character


def refresh_characters(*, fetch=client.find_data_chunk, cache=images.cache_asset) -> int:
    text = fetch("characters")
    raw = extract.parse_characters(text)
    count = 0
    with get_connection() as conn:
        existing = {
            r["id"]: r["role"]
            for r in conn.execute("SELECT id, role FROM character_catalog").fetchall()
        }
        for item in raw:
            rec = normalize_character(item)
            rec["image"] = cache("characters", "iconrolehead150", rec.pop("head_icon_asset"))
            role = existing.get(rec["id"], "main_dps")
            rec["role"] = role
            conn.execute(
                """
                INSERT INTO character_catalog (id, name, role, data_json, updated_at)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, data_json=EXCLUDED.data_json, updated_at=now()
                """,
                (rec["id"], rec["name"], role, json.dumps(rec, ensure_ascii=False)),
            )
            count += 1
        conn.commit()
    return count
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_wutheringgg_refresh.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/wutheringgg/refresh.py backend/tests/test_wutheringgg_refresh.py
git commit -m "feat: refresh_characters upserts wuthering.gg data into character_catalog"
```

---

### Task 7: Weapons + echoes refresh (mirror Task 6)

**Files:**
- Modify: `backend/src/wutheringgg/normalize.py` (add `normalize_weapon`, `normalize_echo`)
- Modify: `backend/src/wutheringgg/refresh.py` (add `refresh_weapons`, `refresh_echoes`)
- Test: `backend/tests/test_wutheringgg_refresh.py` (add cases)

**Interfaces:**
- Produces: `normalize_weapon(raw) -> dict`, `normalize_echo(raw) -> dict`, `refresh_weapons(...) -> int`, `refresh_echoes(...) -> int`. Upsert into `weapon_catalog` / `echo_catalog` by game `Id`, preserving existing rows' identity where present.

- [ ] **Step 1: Determine live schemas** — run the Task 3 live smoke for weapons and echoes:

Run: `cd backend && uv run python -c "from src.wutheringgg import client, extract; import json; w=extract.parse_weapons(client.find_data_chunk('weapons')); print(len(w)); print(sorted(w[0].keys()))"`
Record the weapon key set. Repeat for echoes (`parse_echoes`). Write `normalize_weapon`/`normalize_echo` mapping exactly those keys (name, name_en, rarity/QualityId, weapon_type via `WEAPON_TYPE`, stats, passive/effect, icon asset for weapons; name, cost, sonata, klass, skill, icon asset for echoes).

- [ ] **Step 2: Write failing tests** for `normalize_weapon`/`normalize_echo` using two real objects captured as inline dicts (mirror Task 4's test structure with the actual keys recorded in Step 1).

- [ ] **Step 3: Run tests to verify they fail.** Run: `cd backend && uv run pytest tests/test_wutheringgg_refresh.py -q` → FAIL.

- [ ] **Step 4: Implement `normalize_weapon`/`normalize_echo` and `refresh_weapons`/`refresh_echoes`**, each mirroring Task 6's `refresh_characters` (discover → parse → normalize → cache icon → upsert by Id into the respective table, preserving identity).

- [ ] **Step 5: Run tests to verify they pass.** Run: `cd backend && uv run pytest tests/test_wutheringgg_refresh.py -q` → PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/wutheringgg/normalize.py backend/src/wutheringgg/refresh.py backend/tests/test_wutheringgg_refresh.py
git commit -m "feat: weapons + echoes refresh from wuthering.gg"
```

---

### Task 8: Live run + verification (parallel image caching)

**Files:**
- Create: `backend/scripts/run_wutheringgg_refresh.py` (a thin runnable entrypoint)

**Interfaces:**
- Consumes: `refresh_characters`, `refresh_weapons`, `refresh_echoes`.

- [ ] **Step 1: Write the entrypoint**

```python
# backend/scripts/run_wutheringgg_refresh.py
"""One-shot: refresh all wuthering.gg entities into the dev DB."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.database import database_url  # noqa: E402
root, _ = database_url().rsplit("/", 1)
os.environ["DATABASE_URL"] = root + "/wuwa_ai_coach_dev"
from src.wutheringgg import refresh  # noqa: E402

if __name__ == "__main__":
    print("characters:", refresh.refresh_characters())
    print("weapons:", refresh.refresh_weapons())
    print("echoes:", refresh.refresh_echoes())
```

- [ ] **Step 2: Run it** (this is the token-heavy image-download step; the controller may fan this out via a Workflow — one agent per entity type + batched image downloads — but the entrypoint above is the deterministic fallback).

Run: `cd backend && uv run python scripts/run_wutheringgg_refresh.py`
Expected: prints non-zero counts for each (characters ≈ 53).

- [ ] **Step 3: Verify** in the dev DB:

```bash
cd backend && uv run python -c "
import os; from src.database import database_url; root,_=database_url().rsplit('/',1); os.environ['DATABASE_URL']=root+'/wuwa_ai_coach_dev'
from src.database import get_connection; import json
with get_connection() as c:
    d=json.loads(c.execute(\"SELECT data_json FROM character_catalog WHERE id=1603\").fetchone()['data_json'])
print('Camellya:', d['name'], d['element'], d['weapon_type'], d['rarity'], '| skills', len(d['skills']), '| chain', len(d['resonance_chain']), '| img', d['image'])
"
```
Expected: `Camellya: 카멜리아 인멸 Sword 5 | skills 10 | chain 6 | img /catalog/image/characters/...`

- [ ] **Step 4: Run the full backend suite** to confirm no regressions (pickup `catalog_id` join still resolves).

Run: `cd backend && uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/run_wutheringgg_refresh.py
git commit -m "feat: wuthering.gg refresh entrypoint + verified live load"
```

---

## Self-Review

**Spec coverage:** Discovery (Task 3) ✓, extraction (Tasks 1-2) ✓, normalization + enum maps + image URLs (Task 4) ✓, image caching (Task 5) ✓, storage/upsert by game Id preserving consumers (Tasks 6-7) ✓, parallel run (Task 8) ✓, testing via committed fixture + unit tests ✓, dev-DB isolation ✓. Editorial content (tier/prose) explicitly out of scope per spec ✓.

**Placeholder scan:** Task 7 Steps 1-4 intentionally defer exact weapon/echo key mapping to a live-schema capture step (the keys are only knowable from the live chunk); every other task carries complete code. Task 5 Step 5 / Task 7 are the only prose-with-commands steps, and each names the exact command to run and what to record.

**Type consistency:** `find_data_chunk(kind)` returns text consumed by `parse_*`; `normalize_character` output keys match Task 6's `rec[...]` usage (`id`, `name`, `weapon_type`, `image`, `role`); `cache_asset(kind, category, asset)` signature matches Task 6's `cache(...)` call and Task 6's test stub.
