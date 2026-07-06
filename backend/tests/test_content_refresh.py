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
