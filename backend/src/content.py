from __future__ import annotations

import json
from pathlib import Path

from .models import GameUpdateSummary, PickupScheduleItem, SiteUpdateEntry

# 정적 스냅샷 정본(무DB). 재생성: scripts/export_content_to_files.py (DB 살아있을 때 1회).
_CONTENT_DIR = Path(__file__).resolve().parents[1] / "data" / "content"


def _read(name: str):
    path = _CONTENT_DIR / name
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_game_config() -> dict:
    """Game-math constants (echo stat tables etc.) keyed by config id."""
    data = _read("game_config.json")
    return data if isinstance(data, dict) else {}


def load_pickup_schedule(year: int | None = None) -> list[PickupScheduleItem]:
    items = [PickupScheduleItem.model_validate(row) for row in _read("pickup_schedule.json")]
    if year is not None:
        items = [it for it in items if it.year == year]
    return items


def load_game_updates() -> list[GameUpdateSummary]:
    return [GameUpdateSummary.model_validate(row) for row in _read("game_updates.json")]


def load_site_updates() -> list[SiteUpdateEntry]:
    return [SiteUpdateEntry.model_validate(row) for row in _read("site_updates.json")]
