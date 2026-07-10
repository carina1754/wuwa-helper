"""Seed the 0.4.2 site-update (공지사항) entry. Idempotent (upsert by id).

Usage: uv run python scripts/seed_release_042.py   (targets DATABASE_URL)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection  # noqa: E402

ENTRY = {
    "id": "release-0-4-2-2026-07-10",
    "date": "2026-07-10",
    "version": "0.4.2",
    "title_ko": "0.4.2 업데이트",
    "description_ko": (
        "• 공명 사슬 반영: 캐릭터별 공명 사슬(시퀀스) S0~S6 단계를 파티·빌드 딜 계산에 반영합니다. "
        "각 단계 효과 수치는 실제 게임 데이터를 기준으로 하며, 수치화가 어려운 조건부·메커니즘 효과는 별도로 표기합니다.\n"
        "• 파티 편집기에 공명 사슬 단계(S0~S6) 선택 기능을 추가했습니다.\n"
        "• 도감 정리: 방랑자·회절의 중복 표시되던 스킬 설명을 하나로 정리했습니다."
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
