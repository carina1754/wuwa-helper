"""Seed the 0.3.1 site-update (공지사항) entry. Idempotent (upsert by id).

Usage: uv run python scripts/seed_release_031.py   (targets DATABASE_URL)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection  # noqa: E402

ENTRY = {
    "id": "release-0-3-1-2026-07-08",
    "date": "2026-07-08",
    "version": "0.3.1",
    "title_ko": "0.3.1 업데이트",
    "description_ko": (
        "• 데미지 계산기: 파티 탭에서 일반·이상·조화도 파괴 데미지를 계산하고, 적 레벨·저항·방어무시 등 조건을 직접 조정할 수 있습니다.\n"
        "• 무기 패시브 반영: 무기의 상시 버프가 최종 스탯에 자동 반영되며, 조건부 효과는 '풀 업타임' 토글로 최대 스택까지 계산합니다.\n"
        "• 이상 효과 정교화: 캐릭터 속성에 따라 이상 유형(응결→서리 등)이 자동 선택되고, 암흑(방어 감소) 디버프가 파티 전체 피해에 반영됩니다.\n"
        "• 공지사항 디자인 개선: 업데이트 내역을 더 읽기 쉽게 정리했습니다."
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
