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
    "title_en": "0.4.1 Update",
    "title_ja": "0.4.1 アップデート",
    "title_zhHans": "0.4.1 更新",
    "description_en": (
        "• New characters: added Yangyang: Xuanling, Suisui, and Rover: Electro, and tidied up the Rover list.\n"
        "• New weapons: added 'Azure Oath' and 'Firstlight's Herald'.\n"
        "• Codex icons: replaced character icons with sharper, high-resolution images.\n"
        "• Data accuracy: recalibrated character, weapon, echo, and sonata values to the game's 3.5.0 data for more accurate calculations."
    ),
    "description_ja": (
        "• 新キャラクター:秧秧・玄翎、穂穂、漂泊者・電導を追加し、漂泊者(ローバー)一覧を整理しました。\n"
        "• 新武器:「天つ蒼淵」「夕霞の飲露」を追加しました。\n"
        "• 図鑑アイコン:キャラクターアイコンをより鮮明な高解像度画像に差し替えました。\n"
        "• データ精度:キャラクター・武器・エコー・ソナタの数値をゲーム3.5.0データ基準で再整備し、計算精度を高めました。"
    ),
    "description_zhHans": (
        "• 新角色:新增秧秧·玄翎、穗穗、漂泊者·导电,并整理了漂泊者名单。\n"
        "• 新武器:新增「天之苍苍」「栖霞饮露」。\n"
        "• 图鉴图标:将角色图标替换为更清晰的高分辨率图片。\n"
        "• 数据准确度:以游戏3.5.0数据为准重新整理角色·武器·声骸·合鸣数值,提升计算准确度。"
    ),
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
