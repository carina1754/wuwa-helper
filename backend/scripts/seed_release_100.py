"""Seed the 1.0.0 site-update (공지사항) entry — 정식 릴리스. Idempotent (upsert by id).

Usage: uv run python scripts/seed_release_100.py   (targets DATABASE_URL)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection  # noqa: E402

ENTRY = {
    "id": "release-1-0-0-2026-07-10",
    "date": "2026-07-10",
    "version": "1.0.0",
    "title_ko": "1.0.0 정식 버전 출시",
    "description_ko": (
        "띵조 AI가 정식 버전이 되었습니다. 그동안의 업데이트를 모아 아래 기능을 안정적으로 제공합니다.\n"
        "• 파티 딜 계산 — 공명자 3명을 편성하면 서버 엔진이 파티 전체 피해와 기여도를 계산합니다. "
        "팀 공유 버프 자동 적용, 공명 사슬(시퀀스) 반영, 풀 업타임 옵션, 적 조건 설정을 지원합니다.\n"
        "• 도감 — 전 공명자·무기·에코 정보와 스킬 배율(레벨별 총합)을 제공합니다.\n"
        "• 픽업 일정표 — 버전별 픽업 배너 일정을 한눈에 볼 수 있습니다.\n"
        "• 실측 딜 — 캐릭터 정보 스크린샷을 올리면 실제 에코 부가옵션을 반영한 절대 피해를 계산합니다.\n"
        "• AI 빌딩 — 보유 캐릭터와 목표를 알려주면 AI가 빌드와 파티를 추천하고 기록으로 저장합니다. "
        "캐릭터는 아이콘으로 검색·선택할 수 있고, 플레이 스타일은 직접 입력할 수 있습니다.\n"
        "• 이용 가이드 — 상단 ? 아이콘에서 스크린샷과 함께 모든 기능의 사용법을 확인할 수 있습니다.\n"
        "• 보안·성능 — 관리용 API 보호를 강화하고 첫 로딩 용량을 크게 줄였습니다.\n"
        "이용해 주셔서 감사합니다. 개선 요청과 버그 제보는 디스코드로 남겨주세요."
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
