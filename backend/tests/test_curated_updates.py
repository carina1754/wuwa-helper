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
    update_id = "test-curated-99-9"
    monkeypatch.setattr(
        curated_updates,
        "CURATED_UPDATE_SUMMARIES",
        {"99.9": {"summary_ko": "테스트 요약", "highlights_ko": ["항목1", "항목2"]}},
    )
    with get_connection() as conn:
        conn.execute("DELETE FROM game_updates WHERE id = %s", (update_id,))
        conn.execute(
            "INSERT INTO game_updates (id, version, release_date_kst, data_json, updated_at)"
            " VALUES (%s, %s, %s, %s, now())",
            (
                update_id,
                "99.9",
                "2026-06-08",
                json.dumps(
                    {
                        "id": update_id,
                        "version": "99.9",
                        "title_ko": "「選択しなかった夢」99.9 バージョン",
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
