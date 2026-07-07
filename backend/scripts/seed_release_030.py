"""Seed the 0.3.0 site-update (공지사항) entry. Idempotent (upsert by id).

Usage: uv run python scripts/seed_release_030.py   (targets DATABASE_URL)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection  # noqa: E402

ENTRY = {
    "id": "release-0-3-0-2026-07-07",
    "date": "2026-07-07",
    "version": "0.3.0",
    "title_ko": "0.3.0 업데이트",
    "description_ko": (
        "• 게임 데이터 전면 갱신: 캐릭터·무기·에코의 완전한 수치 데이터로 교체했습니다.\n"
        "• 도감·픽업 상세에 레벨 슬라이더 추가: 레벨(1~90)별로 공격력·HP·방어력·크리티컬 등 스탯을 직접 확인할 수 있습니다.\n"
        "• 파티 탭 신설: 공명자 3명으로 파티를 구성하고 역할·속성 시너지를 확인합니다.\n"
        "• 픽업 상세를 도감과 통일: 픽업 일정표에서도 캐릭터·무기 상세를 도감과 동일하게 봅니다.\n"
        "• 기타: 상세 모달 표시 버그 수정, 공지 아이콘 변경, 옛 데이터 정리."
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
