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


def test_pickup_schedule_seed_keeps_corrected_mid_2026_banners():
    items = _load_items()
    by_id = {item["id"]: item for item in items}
    assert by_id["2026-06-08-lucy-first_pickup"]["characters"] == ["Lucy"]
    assert by_id["2026-06-08-lucy-first_pickup"]["end_date"] == "2026-07-09"
    assert by_id["2026-06-13-lucilla-first_pickup"]["characters"] == ["Lucilla"]
    assert by_id["2026-06-18-cartethyia-rerun_2"]["characters"] == ["Cartethyia"]


def test_pickup_schedule_seed_allows_rerun_3():
    items = _load_items()
    rerun_3_items = [item for item in items if item["category"] == "rerun_3"]
    assert rerun_3_items
    for item in rerun_3_items:
        PickupScheduleItem.model_validate(item)
