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
    "title_en": "0.4.3 Update",
    "title_ja": "0.4.3 アップデート",
    "title_zhHans": "0.4.3 更新",
    "description_en": (
        "• Automatic team-shared buffs: just place characters in your party, and the shared buffs each character grants the whole team (Concerto, inherent traits, Forte Circuit, etc.) plus the debuffs they apply to enemies are automatically reflected in damage calculations. Team buffs you used to enter by hand are now handled for you.\n"
        "• Organized the team-shared buffs of all 56 Resonators based on real game data. Conditional and summon-mechanic effects that are hard to quantify are shown as separate notes.\n"
        "• Buffs are now applied only to their matching skill type (Basic Attack, Heavy Attack, Resonance Skill, Resonance Liberation) to prevent overestimation.\n"
        "• Added an 'auto-applied team buffs' section to each member card in the party editor so you can see at a glance which buffs are in effect."
    ),
    "description_ja": (
        "• チーム共有バフの自動適用:パーティにキャラクターを編成するだけで、各キャラクターがパーティ全体に与える共有バフ(コンチェルト・固有特性・共鳴回路など)と敵に付与するデバフが自動でダメージ計算に反映されます。以前は手動で入力していたチームバフを自動で処理します。\n"
        "• 56人全共鳴者のチーム共有バフを実際のゲームデータ基準で整理しました。数値化が難しい条件付き・召喚メカニズム効果は別途の案内で表記します。\n"
        "• スキルタイプ別(通常攻撃・強攻撃・共鳴スキル・共鳴解放)のバフは該当タイプのスキルにのみ正確に適用されるようにし、過大計算を防止しました。\n"
        "• パーティ編集画面の各メンバーカードに「自動適用チームバフ」項目を追加し、どのバフが反映されたかをすぐ確認できます。"
    ),
    "description_zhHans": (
        "• 队伍共享增益自动生效:只要将角色编入队伍,各角色为全队提供的共享增益(协奏·固有特性·共鸣回路等)以及施加给敌人的减益都会自动计入伤害计算。以往需要手动输入的队伍增益现在会自动处理。\n"
        "• 以实际游戏数据为准整理了全部56名共鸣者的队伍共享增益。难以量化的条件类·召唤机制类效果以单独说明标注。\n"
        "• 各技能类型(普通攻击·重击·共鸣技能·共鸣解放)的增益现仅精确应用于对应类型的技能,避免了数值高估。\n"
        "• 在队伍编辑器的每张成员卡中新增「自动生效队伍增益」项,可一眼查看哪些增益已计入。"
    ),
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
