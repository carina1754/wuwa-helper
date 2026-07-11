"""Seed the 1.0.1 site-update (공지사항) entry. Idempotent (upsert by id).

Usage: uv run python scripts/seed_release_101.py   (targets DATABASE_URL)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection  # noqa: E402

ENTRY = {
    "id": "release-1-0-1-2026-07-12",
    "date": "2026-07-12",
    "version": "1.0.1",
    "title_ko": "1.0.1 · 3.5 신규 에코 · AI 빌딩 개선",
    "description_ko": (
        "명조 3.5 신규 콘텐츠와 사용성 개선을 반영했습니다.\n"
        "• 3.5 신규 에코 — 에코 20종과 신규 소나타 3종(내려앉은 깃털의 노래·악을 씻어내는 마음·황천길을 밝히는 등불)을 도감·파티 빌딩에 반영했습니다.\n"
        "• 스탯 정확도 향상 — 포르테(스킬트리) 고정 스탯 보너스를 반영해 파티·실측 딜 수치가 인게임 패널에 더 가깝게 나옵니다.\n"
        "• AI 메인 딜러 지정 — 파티 빌딩에서 원하는 캐릭터를 메인 딜러로 직접 지정할 수 있습니다(역할 태그와 무관하게 빌드·평가).\n"
        "• AI 이름 구분 개선 — 채팅에서 '치사'와 '치샤'처럼 비슷한 이름을 정확히 구분합니다.\n"
        "• 픽업 일정 정정 — 3.5 배너 전환 일정을 바로잡았습니다(7월 31일 → 30일)."
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
