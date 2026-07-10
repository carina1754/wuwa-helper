"""Seed the 0.4.1 site-update (공지사항) entry. Idempotent (upsert by id).

Usage: uv run python scripts/seed_release_041.py   (targets DATABASE_URL)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection  # noqa: E402

ENTRY = {
    "id": "release-0-4-1-2026-07-10",
    "date": "2026-07-10",
    "version": "0.4.1",
    "title_ko": "0.4.1 업데이트",
    "description_ko": (
        "• 신규 캐릭터: 양양·현령, 수수, 방랑자·전도를 추가하고 방랑자(로버) 목록을 정리했습니다.\n"
        "• 신규 무기: '아득히 푸른 하늘', '노을에 깃든 이슬'을 추가했습니다.\n"
        "• 도감 아이콘: 캐릭터 아이콘을 더 선명한 고해상도 이미지로 교체했습니다.\n"
        "• 데이터 정확도: 캐릭터·무기·에코·소나타 수치를 게임 3.5.0 데이터 기준으로 재정비해 계산 정확도를 높였습니다."
    ),
}


def main() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO site_updates (id, date, version, title_ko, description_ko, data_json, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE SET
                date=EXCLUDED.date, version=EXCLUDED.version, title_ko=EXCLUDED.title_ko,
                description_ko=EXCLUDED.description_ko, data_json=EXCLUDED.data_json, updated_at=now()
            """,
            (
                ENTRY["id"], ENTRY["date"], ENTRY["version"], ENTRY["title_ko"],
                ENTRY["description_ko"], json.dumps(ENTRY, ensure_ascii=False),
            ),
        )
        conn.commit()
    print(f"seeded site-update {ENTRY['id']} (v{ENTRY['version']})")


if __name__ == "__main__":
    main()
