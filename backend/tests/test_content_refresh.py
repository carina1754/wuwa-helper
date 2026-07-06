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
        conn.execute(
            """
            INSERT OR REPLACE INTO game_updates (id, version, release_date_kst, data_json, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (
                "test-historical-update",
                "1.0",
                "2020-01-01",
                json.dumps(
                    {
                        "id": "test-historical-update",
                        "version": "1.0",
                        "title_ko": "1.0 업데이트",
                        "release_date_kst": "2020-01-01",
                        "summary_ko": "historical update row that must survive a refresh",
                        "highlights_ko": [],
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
            "game_updates": [
                {
                    "id": "test-current-update",
                    "version": "2.0",
                    "title_ko": "2.0 업데이트",
                    "release_date_kst": "2026-08-01",
                    "summary_ko": "freshly scraped current update",
                    "highlights_ko": [],
                    "source_links": [],
                }
            ],
        },
    )

    result = content_refresh.refresh_pickups_and_updates(force=True)
    assert result["refreshed"] is True

    with get_connection() as conn:
        ids = {row["id"] for row in conn.execute("SELECT id FROM pickup_schedule").fetchall()}
        update_ids = {row["id"] for row in conn.execute("SELECT id FROM game_updates").fetchall()}

    assert "test-historical-row" in ids
    assert "test-current-row" in ids
    assert "test-historical-update" in update_ids
    assert "test-current-update" in update_ids


def test_scraper_pickup_schedule_id_matches_seed_convention(monkeypatch, tmp_path):
    """Regression test for the scraper producing a differently-formatted id.

    `_schedule_from_banner_rows` (used on the non-JSON-feed / live scraper path)
    must generate ids using the same `{year}-{month:02d}-{suffix}` convention as
    the seed data (`first_pickup` -> `first`, `rerun_1` -> `rerun-1`), so the
    upsert in `refresh_pickups_and_updates` updates the existing seeded row for
    a given year/month instead of inserting a duplicate row alongside it.
    """
    db_path = tmp_path / "test_content_refresh_scraper.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    init_db()

    # Seed a historical row using the seed's id convention for 2026-07 first_pickup,
    # matching the real backend/data/pickup_schedule.json entry "2026-07-first".
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO pickup_schedule (id, year, month, category, data_json, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                "2026-07-first",
                2026,
                7,
                "first_pickup",
                json.dumps(
                    {
                        "id": "2026-07-first",
                        "year": 2026,
                        "month": 7,
                        "category": "first_pickup",
                        "label_ko": "첫 픽업",
                        "characters": ["Lucy", "Rebecca"],
                        "notes_ko": "seed row for 2026-07 first pickup",
                        "source_links": [],
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        conn.commit()

    # Ensure the JSON-feed branch is NOT used, so the scraper path
    # (_fetch_text -> _extract_banner_rows -> _schedule_from_banner_rows) runs instead.
    monkeypatch.delenv("CONTENT_REFRESH_JSON_URL", raising=False)

    # Synthetic text that `_extract_banner_rows` can parse into a single banner row:
    # banner name line, four-stars-or-N/A line, then a date-range line matching
    # its `date_pattern`. This becomes the sole (and therefore "first_pickup")
    # banner for year=2026, month=7.
    synthetic_text = "Lucy: Whiteout\nN/A\nJuly 1, 2026 - July 21, 2026\n"
    monkeypatch.setattr(content_refresh, "_fetch_text", lambda url: synthetic_text)

    result = content_refresh.refresh_pickups_and_updates(force=True)
    assert result["refreshed"] is True

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id FROM pickup_schedule WHERE id LIKE '2026-07-%'"
        ).fetchall()
    ids = [row["id"] for row in rows]

    # Exactly one row for 2026-07 first_pickup: the scraper must have updated the
    # existing seed row in place, not inserted a duplicate with a differently
    # formatted id such as "2026-07-first_pickup".
    assert ids.count("2026-07-first") == 1
    assert "2026-07-first_pickup" not in ids
