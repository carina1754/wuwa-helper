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
    "title_en": "0.3.0 Update",
    "title_ja": "0.3.0 アップデート",
    "title_zhHans": "0.3.0 更新",
    "description_en": (
        "• Full game-data refresh: replaced character, weapon, and echo stats with complete numeric data.\n"
        "• Level slider in Codex & banner details: check ATK, HP, DEF, Crit and other stats at each level (1–90).\n"
        "• New Party tab: build a party of 3 Resonators and check role & element synergy.\n"
        "• Unified banner details with the Codex: view character and weapon details in the Banner schedule just like in the Codex.\n"
        "• Misc: fixed a detail-modal display bug, changed the announcement icon, cleaned up old data."
    ),
    "description_ja": (
        "• ゲームデータ全面刷新:キャラクター・武器・エコーの完全な数値データに差し替えました。\n"
        "• 図鑑・ピックアップ詳細にレベルスライダー追加:レベル(1〜90)ごとに攻撃力・HP・防御力・クリティカルなどのステータスを直接確認できます。\n"
        "• パーティタブ新設:共鳴者3人でパーティを編成し、ロール・属性のシナジーを確認できます。\n"
        "• ピックアップ詳細を図鑑と統一:ピックアップ日程でもキャラクター・武器の詳細を図鑑と同じように見られます。\n"
        "• その他:詳細モーダルの表示バグ修正、お知らせアイコン変更、旧データ整理。"
    ),
    "description_zhHans": (
        "• 游戏数据全面更新:将角色·武器·声骸替换为完整的数值数据。\n"
        "• 图鉴·抽卡详情新增等级滑块:可按等级(1~90)直接查看攻击力·HP·防御力·暴击等属性。\n"
        "• 新增队伍标签页:用3名共鸣者组队并查看职责·属性的协同。\n"
        "• 抽卡详情与图鉴统一:在抽卡日程中也能像图鉴一样查看角色·武器详情。\n"
        "• 其他:修复详情弹窗显示问题,更换公告图标,清理旧数据。"
    ),
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
