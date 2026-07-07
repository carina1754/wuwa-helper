# Game Updates: Official Hero Image + Curated Korean Summary — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show each 명조/Wuthering Waves version update with its official hero banner image (server-cached) and a human-authored Korean summary + highlights, all stored in PostgreSQL.

**Architecture:** The daily `content_refresh` pipeline gains hero-image caching (download the article's first `<img>` to `backend/media`, serve it via `GET /updates/image/{id}`) and a thematic-title extractor, while never blanking authored summaries. Summaries live in a committed `curated_updates` module and are written into the DB by an idempotent `apply_curated_update_summaries()`. The frontend renders the cached image atop each update card.

**Tech Stack:** FastAPI + psycopg (PostgreSQL, document-in-`data_json` pattern), Next.js 15 / React 19 + Tailwind, pytest (live Postgres, network stubbed via monkeypatch).

## Global Constraints

- Backend Python `>=3.12,<3.13`; manage deps only via `uv add` / `uv add --dev` — never edit `pyproject.toml`/lock by hand. (No new deps are needed for this plan.)
- All content is stored in PostgreSQL (`game_updates.data_json`); do **not** reintroduce file-based seed data.
- **No runtime OpenAI/LLM call** for update summaries; summaries are authored in `backend/src/curated_updates.py`.
- **Dev isolation:** development uses DB `wuwa_ai_coach_dev`, backend port **8001**, frontend port **3001**. Never touch production (ports 3000/8000, DB `wuwa_ai_coach`).
- **Session env (set once, persists for the PowerShell session):** before running any backend command in this plan, set both:
  ```powershell
  $env:DATABASE_URL="postgresql://postgres:<password>@127.0.0.1:5432/wuwa_ai_coach_dev"
  $env:DISABLE_CONTENT_REFRESH="1"
  ```
  The first keeps tests/refresh on the dev DB (the code default is the **prod** DB `wuwa_ai_coach`, so an unset var writes to production). The second stops `main.py`'s background refresh worker from making real network/image calls when `test_api.py` imports the app — explicit `refresh_pickups_and_updates(force=True)` calls in tests still run (they use mocked `_fetch_json`). The per-task `uv run pytest ...` commands assume these are already set.
- Cached images live under `MEDIA_DIR` (default `backend/media`), are git-ignored, and are never committed.
- Frontend renders images with plain `<img>` (no `next/image`); UI copy is Korean.
- Tests make no real network or OpenAI calls (stub with `monkeypatch`).
- Shell is Windows PowerShell; set env vars with `$env:NAME="value"` before the command.

---

### Task 0: Dev environment prerequisites (run first)

**Files:** none (environment setup).

DB-backed tests start at Task 4 (`init_db()` + `get_connection()`), so the dev DB and session env must exist before those tasks run. Do this once at the start of the session.

- [ ] **Step 1: Create the dev database**

```powershell
psql -U postgres -c "CREATE DATABASE wuwa_ai_coach_dev;"
```

Expected: `CREATE DATABASE` (an "already exists" error is fine).

- [ ] **Step 2: Set the session env vars (persist for this PowerShell session)**

```powershell
$env:DATABASE_URL="postgresql://postgres:<password>@127.0.0.1:5432/wuwa_ai_coach_dev"
$env:DISABLE_CONTENT_REFRESH="1"
```

- [ ] **Step 3: Create the schema and verify the connection**

```powershell
cd backend
uv run python -c "from src.database import init_db; init_db(); print('dev schema ready')"
```

Expected: `dev schema ready` (no connection error). The dev DB now has empty tables.

---

### Task 1: Add `image_url` to the game-update model

**Files:**
- Modify: `backend/src/models.py` (class `GameUpdateSummary`, ~line 111-118)
- Test: `backend/tests/test_game_update_model.py` (create)

**Interfaces:**
- Produces: `GameUpdateSummary.image_url: str | None` (default `None`) — the API-relative served path of the cached hero image (e.g. `"/updates/image/wuwa-3-4"`). Consumed by Tasks 6, 7, 8.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_game_update_model.py`:

```python
from __future__ import annotations

from src.models import GameUpdateSummary


def test_image_url_defaults_to_none():
    update = GameUpdateSummary(id="wuwa-3-4", version="3.4", title_ko="t", summary_ko="s")
    assert update.image_url is None


def test_image_url_round_trips_through_json():
    raw = (
        '{"id":"wuwa-3-4","version":"3.4","title_ko":"t","release_date_kst":null,'
        '"summary_ko":"s","highlights_ko":[],"source_links":[],'
        '"image_url":"/updates/image/wuwa-3-4"}'
    )
    update = GameUpdateSummary.model_validate_json(raw)
    assert update.image_url == "/updates/image/wuwa-3-4"
    assert update.model_dump()["image_url"] == "/updates/image/wuwa-3-4"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend; uv run pytest tests/test_game_update_model.py -v`
Expected: FAIL — `test_image_url_round_trips_through_json` errors because `image_url` is not a field (extra key ignored / attribute missing).

- [ ] **Step 3: Add the field**

In `backend/src/models.py`, in `class GameUpdateSummary`, add the field after `source_links`:

```python
class GameUpdateSummary(BaseModel):
    id: str
    version: str
    title_ko: str
    release_date_kst: str | None = None
    summary_ko: str
    highlights_ko: list[str] = Field(default_factory=list)
    source_links: list[str] = Field(default_factory=list)
    image_url: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend; uv run pytest tests/test_game_update_model.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/models.py backend/tests/test_game_update_model.py
git commit -m "feat: add image_url field to GameUpdateSummary"
```

---

### Task 2: Media cache module + gitignore

**Files:**
- Create: `backend/src/media.py`
- Modify: `.gitignore`
- Test: `backend/tests/test_media.py` (create)

**Interfaces:**
- Produces:
  - `media_dir() -> pathlib.Path` — `$MEDIA_DIR` or `backend/media`.
  - `cached_image_path(update_id: str) -> pathlib.Path | None` — existing `MEDIA_DIR/updates/{update_id}.*` or `None`.
  - `download_image(source_url: str, dest: pathlib.Path) -> None` — download with size cap (monkeypatched in tests).
  - `ensure_hero_image(update_id: str, source_url: str | None) -> str | None` — returns `"/updates/image/{update_id}"` when a file is cached (skipping download if already present), else `None`; never raises.
  - Consumed by Tasks 6 (`ensure_hero_image`) and 7 (`cached_image_path`).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_media.py`:

```python
from __future__ import annotations

from src import media


def test_media_dir_honors_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    assert media.media_dir() == tmp_path


def test_ensure_hero_image_none_without_source_or_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    assert media.ensure_hero_image("wuwa-9-9", None) is None


def test_ensure_hero_image_downloads_and_returns_served_path(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))

    def fake_download(url, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"fake-image-bytes")

    monkeypatch.setattr(media, "download_image", fake_download)
    result = media.ensure_hero_image("wuwa-3-4", "https://cdn.example/x.jpg")
    assert result == "/updates/image/wuwa-3-4"
    assert (tmp_path / "updates" / "wuwa-3-4.jpg").read_bytes() == b"fake-image-bytes"


def test_ensure_hero_image_skips_download_when_cached(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    cached = tmp_path / "updates" / "wuwa-3-4.png"
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(b"already-here")

    def boom(url, dest):
        raise AssertionError("must not download when a cached file exists")

    monkeypatch.setattr(media, "download_image", boom)
    assert media.ensure_hero_image("wuwa-3-4", "https://cdn.example/x.jpg") == "/updates/image/wuwa-3-4"


def test_ensure_hero_image_returns_none_on_download_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))

    def boom(url, dest):
        raise OSError("network down")

    monkeypatch.setattr(media, "download_image", boom)
    assert media.ensure_hero_image("wuwa-3-4", "https://cdn.example/x.jpg") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend; uv run pytest tests/test_media.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.media'`.

- [ ] **Step 3: Implement the module**

Create `backend/src/media.py`:

```python
from __future__ import annotations

import os
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"
MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB safety cap
_USER_AGENT = "WuWaHelper/1.0"
_KNOWN_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def media_dir() -> Path:
    override = os.getenv("MEDIA_DIR")
    return Path(override) if override else DEFAULT_MEDIA_DIR


def updates_image_dir() -> Path:
    return media_dir() / "updates"


def cached_image_path(update_id: str) -> Path | None:
    directory = updates_image_dir()
    if not directory.exists():
        return None
    matches = sorted(directory.glob(f"{update_id}.*"))
    return matches[0] if matches else None


def _extension_for(source_url: str) -> str:
    lowered = source_url.lower().split("?", 1)[0]
    for ext in _KNOWN_EXTS:
        if lowered.endswith(ext):
            return ext
    return ".jpg"


def download_image(source_url: str, dest: Path) -> None:
    request = Request(source_url, headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=30) as response:
        data = response.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"image exceeds {MAX_IMAGE_BYTES} bytes: {source_url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def ensure_hero_image(update_id: str, source_url: str | None) -> str | None:
    """Return the API-relative served path for the cached hero image, or None.

    Reuses an already-cached file (no re-download). A failed download yields
    None so the caller (refresh) can continue rather than aborting.
    """
    if cached_image_path(update_id) is not None:
        return f"/updates/image/{update_id}"
    if not source_url:
        return None
    dest = updates_image_dir() / f"{update_id}{_extension_for(source_url)}"
    try:
        download_image(source_url, dest)
    except Exception:
        return None
    return f"/updates/image/{update_id}"
```

- [ ] **Step 4: Add gitignore entries**

Append to `.gitignore`:

```
media/
backend/media/
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend; uv run pytest tests/test_media.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/src/media.py backend/tests/test_media.py .gitignore
git commit -m "feat: add hero-image cache module for game updates"
```

---

### Task 3: content_refresh extraction helpers (hero image URL + thematic title)

**Files:**
- Modify: `backend/src/content_refresh.py` (add two helpers near the other `_extract_*` functions, ~line 67-110)
- Test: `backend/tests/test_content_refresh.py` (append tests)

**Interfaces:**
- Produces:
  - `_extract_hero_image_url(raw_content: str) -> str | None` — first `<img src="...">` in raw article HTML.
  - `_extract_thematic_title(article_title: str, version: str) -> str` — `"「...」 X.Y 버전"` for content-notice articles, else `"{version} 업데이트"`.
  - Consumed by Task 5.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_content_refresh.py`:

```python
def test_extract_hero_image_url_finds_first_img():
    content = 'intro <p><img src="https://cdn.example/hero.jpg" alt="x" /></p> tail'
    assert content_refresh._extract_hero_image_url(content) == "https://cdn.example/hero.jpg"


def test_extract_hero_image_url_none_without_img():
    assert content_refresh._extract_hero_image_url("no images here") is None


def test_extract_thematic_title_strips_content_notice_suffix():
    title = "「선택하지 않은 꿈」 3.4 버전 내용 안내"
    assert content_refresh._extract_thematic_title(title, "3.4") == "「선택하지 않은 꿈」 3.4 버전"


def test_extract_thematic_title_falls_back_for_non_content_articles():
    title = "Wuthering Waves Version 3.5 Update Maintenance Notice"
    assert content_refresh._extract_thematic_title(title, "3.5") == "3.5 업데이트"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend; uv run pytest tests/test_content_refresh.py -k "hero_image_url or thematic_title" -v`
Expected: FAIL — `AttributeError: module 'src.content_refresh' has no attribute '_extract_hero_image_url'`.

- [ ] **Step 3: Implement the helpers**

In `backend/src/content_refresh.py`, add after `_extract_version_from_article` (~line 72):

```python
def _extract_hero_image_url(raw_content: str) -> str | None:
    match = re.search(r'<img[^>]+src="([^"]+)"', raw_content, re.IGNORECASE)
    return match.group(1) if match else None


def _extract_thematic_title(article_title: str, version: str) -> str:
    title = (article_title or "").strip()
    if "내용 안내" in title:
        stripped = re.sub(r"\s*내용\s*안내\s*$", "", title).strip()
        return stripped or f"{version} 업데이트"
    return f"{version} 업데이트"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend; uv run pytest tests/test_content_refresh.py -k "hero_image_url or thematic_title" -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/content_refresh.py backend/tests/test_content_refresh.py
git commit -m "feat: extract hero image url and thematic title from official articles"
```

---

### Task 4: Curated summaries module + idempotent apply

**Files:**
- Create: `backend/src/curated_updates.py`
- Test: `backend/tests/test_curated_updates.py` (create)

**Interfaces:**
- Produces:
  - `CURATED_UPDATE_SUMMARIES: dict[str, dict]` — keyed by version string; each value `{"summary_ko": str, "highlights_ko": list[str]}`.
  - `apply_curated_update_summaries() -> int` — writes authored summaries into matching `game_updates` rows (matched by `version`); returns the count of rows changed; idempotent (second run returns 0).
  - Consumed by Tasks 6 (refresh) and 7 (startup).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_curated_updates.py`:

```python
from __future__ import annotations

import json
import re

from src import curated_updates
from src.database import get_connection, init_db


def test_curated_summaries_have_valid_shape():
    assert curated_updates.CURATED_UPDATE_SUMMARIES
    for version, payload in curated_updates.CURATED_UPDATE_SUMMARIES.items():
        assert re.fullmatch(r"\d+\.\d+", version), version
        assert payload["summary_ko"].strip()
        assert 1 <= len(payload["highlights_ko"]) <= 10
        assert all(h.strip() for h in payload["highlights_ko"])


def test_apply_fills_matching_row_and_is_idempotent(monkeypatch):
    init_db()
    update_id = "test-curated-3-4"
    monkeypatch.setattr(
        curated_updates,
        "CURATED_UPDATE_SUMMARIES",
        {"3.4": {"summary_ko": "테스트 요약", "highlights_ko": ["항목1", "항목2"]}},
    )
    with get_connection() as conn:
        conn.execute("DELETE FROM game_updates WHERE id = %s", (update_id,))
        conn.execute(
            "INSERT INTO game_updates (id, version, release_date_kst, data_json, updated_at)"
            " VALUES (%s, %s, %s, %s, now())",
            (
                update_id,
                "3.4",
                "2026-06-08",
                json.dumps(
                    {
                        "id": update_id,
                        "version": "3.4",
                        "title_ko": "「선택하지 않은 꿈」 3.4 버전",
                        "release_date_kst": "2026-06-08",
                        "summary_ko": "",
                        "highlights_ko": [],
                        "source_links": [],
                        "image_url": None,
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        conn.commit()

    assert curated_updates.apply_curated_update_summaries() == 1
    assert curated_updates.apply_curated_update_summaries() == 0

    with get_connection() as conn:
        row = conn.execute("SELECT data_json FROM game_updates WHERE id = %s", (update_id,)).fetchone()
    data = json.loads(row["data_json"])
    assert data["summary_ko"] == "테스트 요약"
    assert data["highlights_ko"] == ["항목1", "항목2"]

    with get_connection() as conn:
        conn.execute("DELETE FROM game_updates WHERE id = %s", (update_id,))
        conn.commit()
```

Note: the second test matches by `version = '3.4'`. It deletes its own `test-curated-3-4` row afterward. If the dev DB already has a real `wuwa-3-4` row, the monkeypatched apply may also update that real row — harmless (idempotent, correct data) and not asserted here. This is expected behavior in the isolated dev DB.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend; uv run pytest tests/test_curated_updates.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.curated_updates'`.

- [ ] **Step 3: Implement the module**

Create `backend/src/curated_updates.py`:

```python
from __future__ import annotations

import json

from .database import get_connection

# Authored Korean summaries per game version. This module is the source of
# truth so the text survives DB resets and deploys with the code;
# apply_curated_update_summaries() writes it into the game_updates rows that
# the refresh discovers. Extend this dict when a new version's article ships
# (see Task 10 in the plan). NOT a full-dataset seed — only editorial text.
CURATED_UPDATE_SUMMARIES: dict[str, dict] = {
    "3.4": {
        "summary_ko": (
            "「선택하지 않은 꿈」 3.4 버전에서는 사이버펑크: 엣지러너 콜라보가 진행되어 "
            "5성 공명자 루시와 레베카가 등장하고, 신규 5성 공명자 루실라가 추가됩니다. "
            "2026년 6월 8일 점검 후 적용됩니다."
        ),
        "highlights_ko": [
            "콜라보 5성 루시(회절·권총) — 메인 딜러, 강공격/일반 공격 특화",
            "콜라보 5성 레베카(전도·권총) — 빠른 협주, 조화도 파괴 증폭",
            "신규 5성 루실라(응결·증폭기) — 스타토치 아카데미 교장",
            "업데이트 점검: 2026년 6월 8일 05:00~12:00 (KST)",
        ],
    },
}


def apply_curated_update_summaries() -> int:
    """Write authored summaries into matching game_updates rows. Idempotent.

    Matches rows by version. Returns the number of rows actually changed
    (0 when everything already matches).
    """
    updated = 0
    with get_connection() as conn:
        for version, payload in CURATED_UPDATE_SUMMARIES.items():
            row = conn.execute(
                "SELECT id, data_json FROM game_updates WHERE version = %s ORDER BY id LIMIT 1",
                (version,),
            ).fetchone()
            if row is None:
                continue
            data = json.loads(row["data_json"])
            if (
                data.get("summary_ko") == payload["summary_ko"]
                and data.get("highlights_ko") == payload["highlights_ko"]
            ):
                continue
            data["summary_ko"] = payload["summary_ko"]
            data["highlights_ko"] = payload["highlights_ko"]
            conn.execute(
                "UPDATE game_updates SET data_json = %s, updated_at = now() WHERE id = %s",
                (json.dumps(data, ensure_ascii=False), row["id"]),
            )
            updated += 1
        conn.commit()
    return updated
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend; uv run pytest tests/test_curated_updates.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/curated_updates.py backend/tests/test_curated_updates.py
git commit -m "feat: add curated update summaries module with idempotent apply"
```

---

### Task 5: Wire thematic title + image source into `_updates_from_official_articles`

**Files:**
- Modify: `backend/src/content_refresh.py` (`_updates_from_official_articles`, ~line 146-168)
- Test: `backend/tests/test_content_refresh.py` (append a test)

**Interfaces:**
- Consumes: `_extract_hero_image_url`, `_extract_thematic_title` (Task 3).
- Produces: each update dict now carries `title_ko` (thematic) and a transient `image_source_url` (CDN URL or `None`). Consumed by Task 6, which pops `image_source_url` before persisting.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_content_refresh.py`:

```python
def test_official_updates_extract_title_and_image_source(monkeypatch):
    korean_menu = {
        "article": [
            {
                "articleId": 4814,
                "articleTitle": "「선택하지 않은 꿈」 3.4 버전 내용 안내",
                "startTime": "2026-06-08 10:00:00",
            }
        ]
    }
    english_menu = {"article": []}
    articles = {
        ("kr", 4814): {
            "articleTitle": "「선택하지 않은 꿈」 3.4 버전 내용 안내",
            "startTime": "2026-06-08 10:00:00",
            "articleContent": (
                '방랑자님 <img src="https://cdn.example/hero-3-4.jpg" /> '
                "3.4 버전 내용 안내 점검 시간: 2026년 6월 8일 05:00"
            ),
        },
    }

    def fake_fetch_official_json(locale: str, filename: str):
        if filename == "MainMenu.json":
            return korean_menu if locale == "kr" else english_menu
        article_id = int(filename.removeprefix("article/").removesuffix(".json"))
        return articles[(locale, article_id)]

    monkeypatch.setattr(content_refresh, "_fetch_official_json", fake_fetch_official_json)

    updates = content_refresh._updates_from_official_articles()

    assert updates[0]["version"] == "3.4"
    assert updates[0]["title_ko"] == "「선택하지 않은 꿈」 3.4 버전"
    assert updates[0]["image_source_url"] == "https://cdn.example/hero-3-4.jpg"
    assert updates[0]["summary_ko"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend; uv run pytest tests/test_content_refresh.py::test_official_updates_extract_title_and_image_source -v`
Expected: FAIL — `KeyError: 'image_source_url'` (and `title_ko` is `"3.4 업데이트"`).

- [ ] **Step 3: Update the builder**

In `backend/src/content_refresh.py`, inside `_updates_from_official_articles`, replace the body of the inner loop that builds `by_version[version]`:

```python
            detail = _fetch_official_json(locale, f"article/{article_id}.json")
            title = str(detail.get("articleTitle") or article.get("articleTitle") or "")
            raw_content = str(detail.get("articleContent") or "")
            content = _plain_text(raw_content)
            version = _extract_version_from_article(title, content)
            if not version or version in by_version:
                continue
            release_datetime = _extract_release_datetime_kst(content)
            by_version[version] = {
                "id": f"wuwa-{version.replace('.', '-')}",
                "version": version,
                "title_ko": _extract_thematic_title(title, version),
                "release_date_kst": release_datetime,
                "summary_ko": "",
                "highlights_ko": [],
                "source_links": [_article_link(locale, article_id)],
                "image_source_url": _extract_hero_image_url(raw_content),
            }
```

(The only substantive changes vs. the original: introduce `raw_content`, derive `content` from it, set `title_ko` via `_extract_thematic_title`, and add `image_source_url`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend; uv run pytest tests/test_content_refresh.py -v`
Expected: PASS — new test passes; the existing `test_official_updates_*` tests still pass (they don't assert `title_ko` and tolerate the extra key).

- [ ] **Step 5: Commit**

```bash
git add backend/src/content_refresh.py backend/tests/test_content_refresh.py
git commit -m "feat: carry thematic title and hero image source through official updates"
```

---

### Task 6: Preserve summaries + cache image + apply, in `refresh_pickups_and_updates`

**Files:**
- Modify: `backend/src/content_refresh.py` (imports at top; the `for item in updates:` loop in `refresh_pickups_and_updates`, ~line 369-381; add apply call before the final `return`)
- Test: `backend/tests/test_content_refresh.py` (append a test)

**Interfaces:**
- Consumes: `ensure_hero_image` (Task 2), `apply_curated_update_summaries` (Task 4), transient `image_source_url` (Task 5).
- Produces: persisted `game_updates` rows whose `summary_ko`/`highlights_ko` are preserved when the scrape is empty and whose `image_url` is set from the cache.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_content_refresh.py`:

```python
def test_refresh_preserves_summary_and_sets_image(monkeypatch, tmp_path):
    init_db()
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    update_id = "test-preserve-update"
    with get_connection() as conn:
        conn.execute("DELETE FROM game_updates WHERE id = %s", (update_id,))
        conn.execute(
            "INSERT INTO game_updates (id, version, release_date_kst, data_json, updated_at)"
            " VALUES (%s, %s, %s, %s, now())",
            (
                update_id,
                "9.9",
                "2099-01-01",
                json.dumps(
                    {
                        "id": update_id,
                        "version": "9.9",
                        "title_ko": "9.9 버전",
                        "release_date_kst": "2099-01-01",
                        "summary_ko": "AUTHORED SUMMARY",
                        "highlights_ko": ["h1"],
                        "source_links": [],
                        "image_url": None,
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        conn.commit()

    monkeypatch.setenv("CONTENT_REFRESH_JSON_URL", "https://example.com/feed.json")
    monkeypatch.setattr(
        content_refresh,
        "_fetch_json",
        lambda url: {
            "pickup_schedule": [],
            "game_updates": [
                {
                    "id": update_id,
                    "version": "9.9",
                    "title_ko": "9.9 버전",
                    "release_date_kst": "2099-01-01",
                    "summary_ko": "",
                    "highlights_ko": [],
                    "source_links": [],
                    "image_source_url": "https://cdn.example/x.jpg",
                }
            ],
        },
    )
    monkeypatch.setattr(
        content_refresh,
        "ensure_hero_image",
        lambda update_id, source_url: f"/updates/image/{update_id}" if source_url else None,
    )

    result = content_refresh.refresh_pickups_and_updates(force=True)
    assert result["refreshed"] is True

    with get_connection() as conn:
        row = conn.execute("SELECT data_json FROM game_updates WHERE id = %s", (update_id,)).fetchone()
    data = json.loads(row["data_json"])
    assert data["summary_ko"] == "AUTHORED SUMMARY"
    assert data["highlights_ko"] == ["h1"]
    assert data["image_url"] == f"/updates/image/{update_id}"
    assert "image_source_url" not in data  # transient key must not persist

    with get_connection() as conn:
        conn.execute("DELETE FROM game_updates WHERE id = %s", (update_id,))
        conn.commit()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend; uv run pytest tests/test_content_refresh.py::test_refresh_preserves_summary_and_sets_image -v`
Expected: FAIL — `summary_ko` is `""` (clobbered) and `image_url` is absent / `image_source_url` leaks into `data_json`.

- [ ] **Step 3: Add imports**

At the top of `backend/src/content_refresh.py`, after `from .database import get_connection`:

```python
from .curated_updates import apply_curated_update_summaries
from .media import ensure_hero_image
```

- [ ] **Step 4: Rewrite the update upsert loop**

In `refresh_pickups_and_updates`, replace the `for item in updates:` block with:

```python
        for item in updates:
            source_image_url = item.pop("image_source_url", None)
            existing_row = conn.execute(
                "SELECT data_json FROM game_updates WHERE id = %s", (item["id"],)
            ).fetchone()
            previous = json.loads(existing_row["data_json"]) if existing_row else {}

            # Preserve authored fields the scrape leaves empty.
            if not item.get("summary_ko"):
                item["summary_ko"] = previous.get("summary_ko", "")
            if not item.get("highlights_ko"):
                item["highlights_ko"] = previous.get("highlights_ko", [])

            # Cache the hero image (no-op if already cached); keep a previously
            # cached image when this refresh has no new source.
            image_url = ensure_hero_image(item["id"], source_image_url)
            item["image_url"] = image_url or previous.get("image_url")

            conn.execute(
                """
                INSERT INTO game_updates (id, version, release_date_kst, data_json, updated_at)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    version = EXCLUDED.version,
                    release_date_kst = EXCLUDED.release_date_kst,
                    data_json = EXCLUDED.data_json,
                    updated_at = now()
                """,
                (item["id"], item["version"], item.get("release_date_kst"), json.dumps(item, ensure_ascii=False)),
            )
```

- [ ] **Step 5: Call apply before the successful return**

In the same function, change the tail from:

```python
        conn.commit()
    return {"refreshed": True, "source": source, "schedule": len(schedule), "updates": len(updates)}
```

to:

```python
        conn.commit()
    apply_curated_update_summaries()
    return {"refreshed": True, "source": source, "schedule": len(schedule), "updates": len(updates)}
```

- [ ] **Step 6: Run the full content_refresh test module**

Run: `cd backend; uv run pytest tests/test_content_refresh.py -v`
Expected: PASS — new test passes; `test_refresh_preserves_historical_rows_not_covered_by_new_scrape` still passes (its items have no `image_source_url`; `ensure_hero_image` runs for real but returns `None` with no cache/source, so no network call).

- [ ] **Step 7: Commit**

```bash
git add backend/src/content_refresh.py backend/tests/test_content_refresh.py
git commit -m "feat: preserve authored summaries and cache hero images on refresh"
```

---

### Task 7: Image-serving route + startup apply in `main.py`

**Files:**
- Modify: `backend/main.py` (imports; startup calls ~line 60-62; new route near the other `/updates` routes ~line 95-97)
- Test: `backend/tests/test_api.py` (append tests)

**Interfaces:**
- Consumes: `cached_image_path` (Task 2), `apply_curated_update_summaries` (Task 4).
- Produces: `GET /updates/image/{update_id}` → cached file (`200`) or `404`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_api.py`:

```python
def test_update_image_route_serves_cached_file(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    updates_dir = tmp_path / "updates"
    updates_dir.mkdir(parents=True)
    (updates_dir / "wuwa-3-4.jpg").write_bytes(b"img-bytes")

    response = client.get("/updates/image/wuwa-3-4")
    assert response.status_code == 200
    assert response.content == b"img-bytes"


def test_update_image_route_404_when_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    response = client.get("/updates/image/does-not-exist")
    assert response.status_code == 404


def test_update_image_route_rejects_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    response = client.get("/updates/image/..%2F..%2Fsecret")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend; uv run pytest tests/test_api.py -k update_image -v`
Expected: FAIL — route returns `404` for the served-file case only because it does not exist yet (all three fail or error on the missing route/response type).

- [ ] **Step 3: Add imports and the route**

In `backend/main.py`, update imports:

```python
import re
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
```

Add to the existing content imports:

```python
from src.curated_updates import apply_curated_update_summaries
from src.media import cached_image_path
```

Add the route after `get_updates` (~line 97):

```python
@app.get("/updates/image/{update_id}")
def get_update_image(update_id: str) -> FileResponse:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", update_id):
        raise HTTPException(status_code=404, detail="Update image not found")
    path = cached_image_path(update_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Update image not found")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})
```

- [ ] **Step 4: Call apply at startup**

Change the startup block from:

```python
init_db()
start_daily_refresh_worker()
```

to:

```python
init_db()
apply_curated_update_summaries()
start_daily_refresh_worker()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend; uv run pytest tests/test_api.py -k update_image -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Run the whole backend suite**

Run: `cd backend; uv run pytest -v`
Expected: PASS (all tests green)

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/tests/test_api.py
git commit -m "feat: serve cached update images and apply curated summaries on startup"
```

---

### Task 8: Frontend — type + hero image rendering

**Files:**
- Modify: `frontend/src/lib/types.ts` (`GameUpdateSummary`, ~line 104-112)
- Modify: `frontend/src/components/UpdatesSummary.tsx`

**Interfaces:**
- Consumes: `image_url` from `GET /updates` (Task 1/6) and the `GET /updates/image/{id}` route (Task 7); `API_BASE_URL` from `@/lib/constants`.

- [ ] **Step 1: Add the type field**

In `frontend/src/lib/types.ts`, add to `interface GameUpdateSummary`:

```typescript
export interface GameUpdateSummary {
  id: string;
  version: string;
  title_ko: string;
  release_date_kst?: string | null;
  summary_ko: string;
  highlights_ko: string[];
  source_links: string[];
  image_url?: string | null;
}
```

- [ ] **Step 2: Render the hero image**

In `frontend/src/components/UpdatesSummary.tsx`, add the import at the top:

```typescript
import { API_BASE_URL } from "@/lib/constants";
```

Replace the `updates.map(...)` `<article>` block with (image on top, existing content moved into a padded body):

```tsx
          {updates.map((update) => (
            <article key={update.id} className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-panel">
              {update.image_url ? (
                <img
                  src={`${API_BASE_URL}${update.image_url}`}
                  alt={update.title_ko}
                  loading="lazy"
                  className="w-full border-b border-slate-200 bg-slate-50 object-cover"
                  style={{ aspectRatio: "16 / 9" }}
                />
              ) : null}
              <div className="p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <span className="rounded-md bg-slate-950 px-2 py-1 text-sm font-semibold text-white">v{update.version}</span>
                    <h3 className="mt-3 text-lg font-semibold text-slate-950">{update.title_ko}</h3>
                  </div>
                  {update.release_date_kst ? (
                    <span className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                      {t.updates.releaseDate}: {update.release_date_kst}
                    </span>
                  ) : null}
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-700">{update.summary_ko}</p>
                {update.highlights_ko.length > 0 ? (
                  <ul className="mt-4 grid gap-2 text-sm text-slate-700">
                    {update.highlights_ko.map((highlight) => (
                      <li key={highlight} className="rounded-md bg-slate-50 px-3 py-2">
                        {highlight}
                      </li>
                    ))}
                  </ul>
                ) : null}
                {update.source_links.length > 0 ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {update.source_links.map((source, index) => (
                      <a key={source} href={source} target="_blank" rel="noreferrer" className="text-sm font-medium text-teal-700 hover:text-teal-900">
                        {t.updates.source} {index + 1}
                      </a>
                    ))}
                  </div>
                ) : null}
              </div>
            </article>
          ))}
```

- [ ] **Step 3: Lint**

Run: `cd frontend; npm run lint`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/components/UpdatesSummary.tsx
git commit -m "feat: show official hero image on update cards"
```

---

### Task 9: Dev environment — configurable backend origin + docs

**Files:**
- Modify: `frontend/next.config.ts`
- Create: `docs/dev-environment.md`

**Interfaces:**
- Produces: `BACKEND_ORIGIN` env drives the `/backend` rewrite target (default `http://127.0.0.1:8000`).

- [ ] **Step 1: Make the rewrite target env-driven**

Replace `frontend/next.config.ts` with:

```typescript
import type { NextConfig } from "next";

const backendOrigin = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  outputFileTracingRoot: __dirname,
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${backendOrigin}/:path*`,
      },
    ];
  },
};

export default nextConfig;
```

- [ ] **Step 2: Verify the frontend still builds config-wise**

Run: `cd frontend; npm run lint`
Expected: no errors.

- [ ] **Step 3: Write the dev-environment doc**

Create `docs/dev-environment.md`:

```markdown
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
```

- [ ] **Step 4: Commit**

```bash
git add frontend/next.config.ts docs/dev-environment.md
git commit -m "feat: configurable backend origin and dev environment docs"
```

---

### Task 10: Author curated summaries for the recent versions

**Files:**
- Modify: `backend/src/curated_updates.py` (extend `CURATED_UPDATE_SUMMARIES`)

**Interfaces:**
- Consumes: nothing new. Extends the dict validated by `test_curated_summaries_have_valid_shape` (Task 4).

This task adds authored entries for the versions that have official Korean
"내용 안내" articles (3.0, 3.1, 3.2, 3.3 — 3.4 already exists from Task 4). Each
summary is written by fetching the official article and reading its content.

- [ ] **Step 1: Fetch each version's article content**

For each of articles 3.3 → 4615, 3.2 → 4449, 3.1 → 4212, 3.0 → 3923, fetch and read the Korean content:

```powershell
cd backend
uv run python -c "import json,urllib.request; req=urllib.request.Request('https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152/kr/article/4615.json', headers={'User-Agent':'WuWaHelper/1.0'}); print(json.load(urllib.request.urlopen(req,timeout=20))['articleContent'][:4000])"
```

(Repeat for 4449, 4212, 3923. Read the `[버전 내용 소개]` / `✦신규 캐릭터✦` / `✦콜라보✦` / event sections.)

- [ ] **Step 2: Add an authored entry per version**

Extend `CURATED_UPDATE_SUMMARIES` in `backend/src/curated_updates.py`. Each entry follows the same shape as `"3.4"`: a 2–3 sentence `summary_ko` naming the headline characters/collab and release timing, plus 4–7 `highlights_ko` bullets (new/collab characters with element·weapon and role, major events, notable systems). Write natural Korean matching the existing tone. Example shape (fill with the real content read in Step 1):

```python
    "3.3": {
        "summary_ko": "「별바다의 끝에서 닿은 메아리」 3.3 버전에서는 … 신규 5성 공명자 …가 추가됩니다. 2026년 4월 30일 점검 후 적용됩니다.",
        "highlights_ko": [
            "신규 5성 …(속성·무기) — 역할",
            "복각 …",
            "신규 이벤트 …",
            "업데이트 점검: 2026년 4월 30일 05:00~12:00 (KST)",
        ],
    },
```

Add `"3.2"`, `"3.1"`, `"3.0"` the same way. Keep versions ordered newest-first for readability.

- [ ] **Step 3: Validate shape**

Run: `cd backend; uv run pytest tests/test_curated_updates.py::test_curated_summaries_have_valid_shape -v`
Expected: PASS (every entry non-empty, 1–10 highlights).

- [ ] **Step 4: Commit**

```bash
git add backend/src/curated_updates.py
git commit -m "content: author curated Korean summaries for versions 3.0-3.3"
```

---

### Task 11: End-to-end verification in the dev environment

**Files:** none (verification only).

This task proves the feature works against a real (dev) DB and browser. It uses the isolated dev environment from Task 9 so production is never touched.

- [ ] **Step 1: Create the dev DB (if not already)**

```powershell
psql -U postgres -c "CREATE DATABASE wuwa_ai_coach_dev;"
```

- [ ] **Step 2: Start the dev backend on 8001**

```powershell
cd backend
$env:DATABASE_URL="postgresql://postgres:<password>@127.0.0.1:5432/wuwa_ai_coach_dev"
uv run uvicorn main:app --host 127.0.0.1 --port 8001
```

(Leave running in its own terminal.)

- [ ] **Step 3: Populate updates + images, then inspect the API**

In another terminal:

```powershell
curl -X POST http://127.0.0.1:8001/content/refresh
curl http://127.0.0.1:8001/updates
```

Expected: the `/updates` JSON has, for the recent versions, a non-empty `summary_ko`, several `highlights_ko`, a thematic `title_ko` (e.g. `「선택하지 않은 꿈」 3.4 버전`), and an `image_url` like `/updates/image/wuwa-3-4`. Confirm the image bytes serve:

```powershell
curl -I http://127.0.0.1:8001/updates/image/wuwa-3-4
```

Expected: `200 OK`, `content-type: image/jpeg`. Confirm files exist under `backend/media/updates/`.

- [ ] **Step 4: Start the dev frontend on 3001 and verify visually**

```powershell
cd frontend
$env:BACKEND_ORIGIN="http://127.0.0.1:8001"
$env:NEXT_PUBLIC_API_BASE_URL="/backend"
npm run dev -- --hostname 127.0.0.1 --port 3001
```

Open the Updates view and confirm each recent version card shows the hero image on top with the Korean summary + highlights below. Use the preview tooling (screenshot + console/network check) to confirm images load via `/backend/updates/image/...` with no console errors.

- [ ] **Step 5: Full test sweep against the dev DB**

```powershell
cd backend
$env:DATABASE_URL="postgresql://postgres:<password>@127.0.0.1:5432/wuwa_ai_coach_dev"
uv run pytest -v
cd ../frontend
npm run lint
```

Expected: backend all green, lint clean.

- [ ] **Step 6: Report results**

Summarize: `/updates` payload sample (one version), the served image status line, and a screenshot of the Updates view. Note any version still missing a summary/image (e.g. future 3.5 with no article) — that is the expected graceful-degradation case.
