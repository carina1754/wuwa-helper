"""Seed the 0.4.0 site-update (공지사항) entry. Idempotent (upsert by id).

Usage: uv run python scripts/seed_release_040.py   (targets DATABASE_URL)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection  # noqa: E402

ENTRY = {
    "id": "release-0-4-0-2026-07-09",
    "date": "2026-07-09",
    "version": "0.4.0",
    "title_ko": "0.4.0 업데이트",
    "description_ko": (
        "• AI 빌딩: 대화형으로 캐릭터·무기·에코·소나타와 업그레이드 순서를 추천받을 수 있습니다. 스크린샷을 올리면 보유 캐릭터를 자동으로 인식합니다.\n"
        "• 파티 딜 지수: 추천 조합의 상대 딜 지수를 계산해 캐릭터별 기여도(%)와 함께 보여줍니다. 표준 빌드 가정 기반의 비교용 수치입니다.\n"
        "• 기록 저장·삭제: 마음에 드는 추천을 '기록' 탭에 저장하고, 필요 없는 기록은 삭제할 수 있습니다.\n"
        "• 화면 정리: 준비 중이던 대시보드를 정리하고 서비스 이름을 '띵조 AI'로 변경했습니다."
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
