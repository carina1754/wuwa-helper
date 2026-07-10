"""Seed the 0.4.3 site-update (공지사항) entry. Idempotent (upsert by id).

Usage: uv run python scripts/seed_release_043.py   (targets DATABASE_URL)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection  # noqa: E402

ENTRY = {
    "id": "release-0-4-3-2026-07-10",
    "date": "2026-07-10",
    "version": "0.4.3",
    "title_ko": "0.4.3 업데이트",
    "description_ko": (
        "• 팀 공유 버프 자동 적용: 파티에 캐릭터를 편성하기만 하면, 각 캐릭터가 파티 전체에 주는 "
        "공유 버프(반주·고유 특성·공명 회로 등)와 적에게 거는 디버프가 자동으로 딜 계산에 반영됩니다. "
        "이전에는 직접 입력해야 했던 팀 버프를 이제 자동으로 처리합니다.\n"
        "• 56명 전 공명자의 팀 공유 버프를 실제 게임 데이터 기준으로 정리했습니다. 수치화가 어려운 "
        "조건부·소환 메커니즘 효과는 별도 안내로 표기합니다.\n"
        "• 스킬 유형별(일반 공격·강공격·공명 스킬·공명 해방) 버프는 해당 유형의 스킬에만 정확히 "
        "적용되도록 반영해 과대 계산을 방지했습니다.\n"
        "• 파티 편집기의 각 멤버 카드에 '자동 적용 팀 버프' 항목을 추가해, 어떤 버프가 반영됐는지 "
        "바로 확인할 수 있습니다."
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
