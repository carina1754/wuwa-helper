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
