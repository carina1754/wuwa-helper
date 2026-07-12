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
    "title_en": "0.4.2 Update",
    "title_ja": "0.4.2 アップデート",
    "title_zhHans": "0.4.2 更新",
    "description_en": (
        "• Resonance Chain applied: each character's Resonance Chain (Sequence) stages S0–S6 are reflected in Party and build damage calculations. The per-stage effect values are based on real game data, and conditional or mechanic effects that are hard to quantify are noted separately.\n"
        "• Added a Resonance Chain stage (S0–S6) selector to the party editor.\n"
        "• Codex cleanup: merged the duplicated skill descriptions of Rover: Spectro into one."
    ),
    "description_ja": (
        "• 共鳴チェーン反映:キャラクターごとの共鳴チェーン(シーケンス)S0〜S6段階をパーティ・ビルドのダメージ計算に反映します。各段階の効果数値は実際のゲームデータに基づき、数値化が難しい条件付き・メカニズム効果は別途表記します。\n"
        "• パーティ編集画面に共鳴チェーン段階(S0〜S6)の選択機能を追加しました。\n"
        "• 図鑑整理:漂泊者・回折で重複表示されていたスキル説明を一つに整理しました。"
    ),
    "description_zhHans": (
        "• 共鸣链生效:将各角色的共鸣链(序列)S0~S6阶段计入队伍·配装伤害计算。各阶段效果数值以实际游戏数据为准,难以量化的条件类·机制类效果另行标注。\n"
        "• 在队伍编辑器中新增共鸣链阶段(S0~S6)选择功能。\n"
        "• 图鉴整理:将漂泊者·衍射重复显示的技能说明合并为一条。"
    ),
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
