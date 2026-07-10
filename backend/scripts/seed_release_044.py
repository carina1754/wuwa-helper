"""Seed the 0.4.4 site-update (공지사항) entry. Idempotent (upsert by id).

Usage: uv run python scripts/seed_release_044.py   (targets DATABASE_URL)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection  # noqa: E402

ENTRY = {
    "id": "release-0-4-4-2026-07-10",
    "date": "2026-07-10",
    "version": "0.4.4",
    "title_ko": "0.4.4 업데이트",
    "description_ko": (
        "• 파티 딜 계산에 '풀 업타임' 옵션을 추가했습니다(기본 켜짐). 켜져 있으면 공명 사슬(시퀀스)·"
        "무기·특성의 조건부 버프를 이상적인 로테이션 기준으로 반영해 실제 최대 딜에 가깝게 계산합니다.\n"
        "• 이전에는 이러한 조건부 효과가 빠져 총딜이 실제보다 크게 낮게 표시됐습니다. 특히 공명 사슬"
        "(시퀀스) 단계별 피해 증가가 정상 반영되어, 상위 시퀀스에서 딜이 크게 오르는 캐릭터의 계산이 "
        "정확해졌습니다.\n"
        "• 실제 계정의 보수적인 수치를 보고 싶다면 '풀 업타임'을 꺼서 상시 발동 버프만으로 계산할 수 "
        "있습니다."
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
