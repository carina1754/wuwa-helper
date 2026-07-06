# Pickup Schedule Historical Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fake placeholder pickup-schedule seed data with real historical character banner data from launch (May 2024) through June 2026, and fix the daily content-refresh job so it stops wiping historical rows.

**Architecture:** `backend/data/pickup_schedule.json` is a static seed file loaded into the `pickup_schedule` SQLite table once, on first run, by `_seed_pickup_schedule` in `backend/src/database.py`. This plan replaces that file's content with real data compiled from a one-time research pass (game8.co's banner history archive), and changes `backend/src/content_refresh.py` so its daily scrape-based refresh no longer deletes the whole table before inserting.

**Tech Stack:** Python 3.12, pytest, SQLite (stdlib `sqlite3`), Pydantic models in `backend/src/models.py`.

## Global Constraints

- Repository path is `C:\Users\JungSu\Desktop\wawa-ai-coach`; backend commands run from `backend/` with `uv run ...`.
- Do not touch the existing `2026-07-first` / `2026-07-rerun-1` entries in `backend/data/pickup_schedule.json` — they were populated by the live PC Gamer scraper and are already real, current data (out of scope for this backfill, which only covers 2024-05 through 2026-06).
- `game_updates` historical backfill and Naver Game Lounge integration are explicitly out of scope (see `docs/superpowers/specs/2026-07-06-pickup-schedule-history-design.md`).
- Every new `pickup_schedule.json` entry must validate against `PickupScheduleItem` in `backend/src/models.py` (`category` is `Literal["first_pickup", "rerun_1", "rerun_2"]`).
- Character names must exactly match spellings already used in `backend/data/character_catalog.json` (verified below) so the frontend's avatar lookup by name still works.

---

### Task 1: Replace historical pickup schedule seed data

**Files:**
- Modify: `backend/data/pickup_schedule.json`
- Create: `backend/tests/test_pickup_schedule_data.py`

**Interfaces:**
- Consumes: `PickupScheduleItem` from `backend/src/models.py` (fields: `id: str, year: int, month: int, category: Literal["first_pickup","rerun_1","rerun_2"], label_ko: str, characters: list[str], notes_ko: str | None, source_links: list[str]`).
- Produces: no new functions — this task only changes seed data and adds a data-validation test.

- [ ] **Step 1: Write the failing data test**

Create `backend/tests/test_pickup_schedule_data.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from src.models import PickupScheduleItem

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "pickup_schedule.json"


def _load_items() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_pickup_schedule_seed_has_no_duplicate_ids():
    items = _load_items()
    ids = [item["id"] for item in items]
    assert len(ids) == len(set(ids))


def test_pickup_schedule_seed_covers_launch_through_2026():
    items = _load_items()
    years = {item["year"] for item in items}
    assert {2024, 2025, 2026}.issubset(years)


def test_pickup_schedule_seed_has_every_month_from_launch():
    items = _load_items()
    months_by_year: dict[int, set[int]] = {}
    for item in items:
        months_by_year.setdefault(item["year"], set()).add(item["month"])
    assert months_by_year[2024] == {5, 6, 7, 8, 9, 10, 11, 12}
    assert months_by_year[2025] == set(range(1, 13))
    assert {1, 2, 3, 4, 5, 6, 7}.issubset(months_by_year[2026])


def test_pickup_schedule_seed_entries_validate():
    items = _load_items()
    for item in items:
        PickupScheduleItem.model_validate(item)


def test_pickup_schedule_seed_keeps_existing_july_2026_entries():
    items = _load_items()
    by_id = {item["id"]: item for item in items}
    assert by_id["2026-07-first"]["characters"] == ["Lucy", "Rebecca"]
    assert by_id["2026-07-rerun-1"]["characters"] == ["Lucilla", "Cartethyia"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest tests/test_pickup_schedule_data.py -v
```

Expected: FAIL on `test_pickup_schedule_seed_covers_launch_through_2026` and `test_pickup_schedule_seed_has_every_month_from_launch` (2024/2025 data doesn't exist yet).

- [ ] **Step 3: Replace `backend/data/pickup_schedule.json` with the full historical dataset**

Replace the entire file content with:

```json
[
  {
    "id": "2024-05-first",
    "year": 2024,
    "month": 5,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Jiyan"],
    "notes_ko": "버전 1.0 1페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2024-06-first",
    "year": 2024,
    "month": 6,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Yinlin", "Jinhsi"],
    "notes_ko": "버전 1.0 2페이즈(Yinlin)·1.1 1페이즈(Jinhsi) 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2024-07-first",
    "year": 2024,
    "month": 7,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Changli"],
    "notes_ko": "버전 1.1 2페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2024-08-first",
    "year": 2024,
    "month": 8,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Zhezhi"],
    "notes_ko": "버전 1.2 1페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2024-09-first",
    "year": 2024,
    "month": 9,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Xiangli Yao", "Shorekeeper"],
    "notes_ko": "버전 1.2 2페이즈(Xiangli Yao)·1.3 1페이즈(Shorekeeper) 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2024-10-rerun-1",
    "year": 2024,
    "month": 10,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Jiyan"],
    "notes_ko": "버전 1.3 2페이즈 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2024-11-first",
    "year": 2024,
    "month": 11,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Camellya"],
    "notes_ko": "버전 1.4 1페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2024-12-rerun-1",
    "year": 2024,
    "month": 12,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Yinlin", "Xiangli Yao"],
    "notes_ko": "버전 1.4 2페이즈 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-01-first",
    "year": 2025,
    "month": 1,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Carlotta", "Roccia"],
    "notes_ko": "버전 2.0 1·2페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-01-rerun-1",
    "year": 2025,
    "month": 1,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Zhezhi", "Jinhsi"],
    "notes_ko": "버전 2.0 1·2페이즈 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-02-first",
    "year": 2025,
    "month": 2,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Phoebe"],
    "notes_ko": "버전 2.1 1페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-03-first",
    "year": 2025,
    "month": 3,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Brant", "Cantarella"],
    "notes_ko": "버전 2.1 2페이즈(Brant)·2.2 1페이즈(Cantarella) 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-03-rerun-1",
    "year": 2025,
    "month": 3,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Changli", "Camellya"],
    "notes_ko": "버전 2.1 2페이즈·2.2 1페이즈 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-04-first",
    "year": 2025,
    "month": 4,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Zani"],
    "notes_ko": "버전 2.3 1페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-04-rerun-1",
    "year": 2025,
    "month": 4,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Shorekeeper"],
    "notes_ko": "버전 2.2 2페이즈 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-04-rerun-2",
    "year": 2025,
    "month": 4,
    "category": "rerun_2",
    "label_ko": "2차 복각",
    "characters": ["Jiyan", "Yinlin", "Zhezhi", "Xiangli Yao", "Phoebe"],
    "notes_ko": "버전 2.3 1페이즈 1주년 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-05-first",
    "year": 2025,
    "month": 5,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Ciaccona"],
    "notes_ko": "버전 2.3 2페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-05-rerun-1",
    "year": 2025,
    "month": 5,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Jinhsi", "Changli", "Carlotta", "Roccia", "Brant"],
    "notes_ko": "버전 2.3 2페이즈 1주년 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-06-first",
    "year": 2025,
    "month": 6,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Cartethyia"],
    "notes_ko": "버전 2.4 1페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-07-first",
    "year": 2025,
    "month": 7,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Lupa", "Phrolova"],
    "notes_ko": "버전 2.4 2페이즈(Lupa)·2.5 1페이즈(Phrolova) 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-08-first",
    "year": 2025,
    "month": 8,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Augusta"],
    "notes_ko": "버전 2.6 1페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-08-rerun-1",
    "year": 2025,
    "month": 8,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Cantarella", "Brant"],
    "notes_ko": "버전 2.5 2페이즈 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-09-first",
    "year": 2025,
    "month": 9,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Iuno"],
    "notes_ko": "버전 2.6 2페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-10-first",
    "year": 2025,
    "month": 10,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Galbrena", "Qiuyuan"],
    "notes_ko": "버전 2.7 1·2페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-10-rerun-1",
    "year": 2025,
    "month": 10,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Lupa"],
    "notes_ko": "버전 2.7 1페이즈 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-10-rerun-2",
    "year": 2025,
    "month": 10,
    "category": "rerun_2",
    "label_ko": "2차 복각",
    "characters": ["Zani"],
    "notes_ko": "버전 2.7 2페이즈 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-11-first",
    "year": 2025,
    "month": 11,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Chisa"],
    "notes_ko": "버전 2.8 1페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-11-rerun-1",
    "year": 2025,
    "month": 11,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Phoebe"],
    "notes_ko": "버전 2.8 1페이즈 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-12-first",
    "year": 2025,
    "month": 12,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Lynae"],
    "notes_ko": "버전 3.0 1페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-12-rerun-1",
    "year": 2025,
    "month": 12,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Phrolova", "Cantarella"],
    "notes_ko": "버전 2.8 2페이즈 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2025-12-rerun-2",
    "year": 2025,
    "month": 12,
    "category": "rerun_2",
    "label_ko": "2차 복각",
    "characters": ["Cartethyia", "Ciaccona"],
    "notes_ko": "버전 3.0 1페이즈 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-01-first",
    "year": 2026,
    "month": 1,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Mornye"],
    "notes_ko": "버전 3.0 2페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-01-rerun-1",
    "year": 2026,
    "month": 1,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Augusta", "Iuno"],
    "notes_ko": "버전 3.0 2페이즈 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-02-first",
    "year": 2026,
    "month": 2,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Aemeath", "Luuk Herssen"],
    "notes_ko": "버전 3.1 1·2페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-02-rerun-1",
    "year": 2026,
    "month": 2,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Chisa", "Lupa"],
    "notes_ko": "버전 3.1 1페이즈 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-02-rerun-2",
    "year": 2026,
    "month": 2,
    "category": "rerun_2",
    "label_ko": "2차 복각",
    "characters": ["Galbrena"],
    "notes_ko": "버전 3.1 2페이즈 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-03-first",
    "year": 2026,
    "month": 3,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Sigrika"],
    "notes_ko": "버전 3.2 1페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-03-rerun-1",
    "year": 2026,
    "month": 3,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Qiuyuan"],
    "notes_ko": "버전 3.2 1페이즈 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-04-first",
    "year": 2026,
    "month": 4,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Hiyuki"],
    "notes_ko": "버전 3.3 1페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-04-rerun-1",
    "year": 2026,
    "month": 4,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Lynae", "Zani", "Phoebe"],
    "notes_ko": "버전 3.2 2페이즈 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-04-rerun-2",
    "year": 2026,
    "month": 4,
    "category": "rerun_2",
    "label_ko": "2차 복각",
    "characters": ["Mornye", "Iuno"],
    "notes_ko": "버전 3.3 1페이즈 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-05-first",
    "year": 2026,
    "month": 5,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Denia"],
    "notes_ko": "버전 3.3 2페이즈 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-05-rerun-1",
    "year": 2026,
    "month": 5,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Chisa", "Phrolova"],
    "notes_ko": "버전 3.3 2페이즈 동시 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-06-first",
    "year": 2026,
    "month": 6,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Lucy", "Lucilla"],
    "notes_ko": "버전 3.4 배너1(Lucy)·배너2(Lucilla) 데뷔 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-06-rerun-1",
    "year": 2026,
    "month": 6,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Cartethyia"],
    "notes_ko": "버전 3.4 배너3 복각 배너",
    "source_links": ["https://game8.co/games/Wuthering-Waves/archives/494979"]
  },
  {
    "id": "2026-07-first",
    "year": 2026,
    "month": 7,
    "category": "first_pickup",
    "label_ko": "첫 픽업",
    "characters": ["Lucy", "Rebecca"],
    "notes_ko": "2026년 7월 기준 Cyberpunk: Edgerunners 콜라보 배너로 확인된 픽업",
    "source_links": ["https://www.pcgamer.com/games/rpg/wuthering-waves-banner-next-current/"]
  },
  {
    "id": "2026-07-rerun-1",
    "year": 2026,
    "month": 7,
    "category": "rerun_1",
    "label_ko": "1차 복각",
    "characters": ["Lucilla", "Cartethyia"],
    "notes_ko": "2026년 7월 9일까지 진행 중으로 확인된 복각/동시 배너",
    "source_links": ["https://www.pcgamer.com/games/rpg/wuthering-waves-banner-next-current/"]
  }
]
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest tests/test_pickup_schedule_data.py -v
```

Expected: PASS (all 5 tests).

- [ ] **Step 5: Delete the local dev database so the new seed data loads**

`_seed_pickup_schedule` in `backend/src/database.py` only inserts seed rows when the `pickup_schedule` table is empty, and the existing local dev DB already has the old (fake) rows. Delete it so it gets rebuilt from the new JSON on next run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
Remove-Item wuwa_ai_coach.db -ErrorAction SilentlyContinue
```

- [ ] **Step 6: Run the full backend test suite**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest -v
```

Expected: all tests PASS (existing tests re-create the DB via `TestClient`'s startup event, so they exercise the fresh seed too).

- [ ] **Step 7: Commit**

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach
git add backend/data/pickup_schedule.json backend/tests/test_pickup_schedule_data.py
git commit -m "feat: backfill real pickup schedule history from launch through June 2026"
```

Note: `backend/wuwa_ai_coach.db` is gitignored (`*.db` in `.gitignore`), so deleting it locally doesn't need a separate commit.

---

### Task 2: Fix content refresh to stop wiping historical rows

**Files:**
- Modify: `backend/src/content_refresh.py`
- Create: `backend/tests/test_content_refresh.py`

**Interfaces:**
- Consumes: `refresh_pickups_and_updates(force: bool = False) -> dict[str, object]` (existing, `backend/src/content_refresh.py`), `get_connection` and `init_db` from `backend/src/database.py`.
- Produces: no new public functions — `refresh_pickups_and_updates` keeps the same signature and return shape, only its internal DB-write behavior changes from delete-then-insert to upsert.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_content_refresh.py`:

```python
from __future__ import annotations

import json

from src import content_refresh
from src.database import get_connection, init_db


def test_refresh_preserves_historical_rows_not_covered_by_new_scrape(monkeypatch, tmp_path):
    db_path = tmp_path / "test_content_refresh.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    init_db()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO pickup_schedule (id, year, month, category, data_json, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                "test-historical-row",
                2020,
                1,
                "first_pickup",
                json.dumps(
                    {
                        "id": "test-historical-row",
                        "year": 2020,
                        "month": 1,
                        "category": "first_pickup",
                        "label_ko": "첫 픽업",
                        "characters": ["HistoricalCharacter"],
                        "notes_ko": "historical row that must survive a refresh",
                        "source_links": [],
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
            "pickup_schedule": [
                {
                    "id": "test-current-row",
                    "year": 2026,
                    "month": 8,
                    "category": "first_pickup",
                    "label_ko": "첫 픽업",
                    "characters": ["NewCharacter"],
                    "notes_ko": "freshly scraped current row",
                    "source_links": [],
                }
            ],
            "game_updates": [],
        },
    )

    result = content_refresh.refresh_pickups_and_updates(force=True)
    assert result["refreshed"] is True

    with get_connection() as conn:
        ids = {row["id"] for row in conn.execute("SELECT id FROM pickup_schedule").fetchall()}

    assert "test-historical-row" in ids
    assert "test-current-row" in ids
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest tests/test_content_refresh.py -v
```

Expected: FAIL — `"test-historical-row" in ids` is false because the current `DELETE FROM pickup_schedule` wipes it before inserting `test-current-row`.

- [ ] **Step 3: Fix the upsert logic**

In `backend/src/content_refresh.py`, find this block inside `refresh_pickups_and_updates` (currently around lines 221–239):

```python
        conn.execute("DELETE FROM pickup_schedule")
        for item in schedule:
            conn.execute(
                """
                INSERT INTO pickup_schedule (id, year, month, category, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                (item["id"], item["year"], item["month"], item["category"], json.dumps(item, ensure_ascii=False)),
            )
        if updates:
            conn.execute("DELETE FROM game_updates")
            for item in updates:
                conn.execute(
                    """
                    INSERT INTO game_updates (id, version, release_date_kst, data_json, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                    """,
                    (item["id"], item["version"], item.get("release_date_kst"), json.dumps(item, ensure_ascii=False)),
                )
```

Replace it with:

```python
        for item in schedule:
            conn.execute(
                """
                INSERT OR REPLACE INTO pickup_schedule (id, year, month, category, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                (item["id"], item["year"], item["month"], item["category"], json.dumps(item, ensure_ascii=False)),
            )
        for item in updates:
            conn.execute(
                """
                INSERT OR REPLACE INTO game_updates (id, version, release_date_kst, data_json, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (item["id"], item["version"], item.get("release_date_kst"), json.dumps(item, ensure_ascii=False)),
            )
```

This replaces the wipe-then-insert with a per-row upsert keyed by `id`, so rows not present in the current scrape (i.e. historical data) are left untouched. The `if updates:` guard is dropped since an empty `updates` list now just means the loop runs zero times — equivalent behavior without the extra branch.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest tests/test_content_refresh.py -v
```

Expected: PASS.

- [ ] **Step 5: Run the full backend test suite**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest -v
```

Expected: all tests PASS, including the Task 1 data tests.

- [ ] **Step 6: Commit**

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach
git add backend/src/content_refresh.py backend/tests/test_content_refresh.py
git commit -m "fix: stop content refresh from wiping historical pickup schedule rows"
```

---

## Manual verification (after both tasks)

Start the backend and confirm the API now serves real multi-year data:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

In another shell:

```powershell
curl http://127.0.0.1:8000/pickup-schedule?year=2024
curl http://127.0.0.1:8000/pickup-schedule?year=2025
curl http://127.0.0.1:8000/pickup-schedule?year=2026
```

Expected: 2024 response has entries for months 5–12, 2025 has all 12 months, 2026 has months 1–7, and July still shows `Lucy, Rebecca` (first pickup) / `Lucilla, Cartethyia` (rerun).
