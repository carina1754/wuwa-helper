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
    "title_en": "1.0.1 · New 3.5 Echoes · AI Build Improvements",
    "title_ja": "1.0.1・3.5新エコー・AIビルド改善",
    "title_zhHans": "1.0.1 · 3.5新声骸 · AI搭配优化",
    "description_en": (
        "Reflects Wuthering Waves 3.5 new content and usability improvements.\n"
        "• New 3.5 echoes — added 20 echoes and 3 new sonatas (Song of Feathered Trace, Heart of Evil's Purge, Lamp of Nether Road) to the Codex and party building.\n"
        "• Improved stat accuracy — Forte (skill-tree) fixed stat bonuses are now reflected, so Party and measured-damage figures come closer to the in-game panel.\n"
        "• AI main-DPS designation — you can pick any character as the main DPS directly in party building (built and evaluated regardless of its role tag).\n"
        "• Improved AI name matching — it now precisely tells apart similar names like 'Chisa' and 'Chixia' in chat.\n"
        "• Banner schedule fix — corrected the 3.5 banner rotation schedule (July 31 → 30)."
    ),
    "description_ja": (
        "鳴潮3.5の新コンテンツと使いやすさの改善を反映しました。\n"
        "• 3.5新エコー — エコー20種と新ソナタ3種(羽舞う塵世の歌・煞を祓う浄心・冥夜を導く灯)を図鑑・パーティビルドに反映しました。\n"
        "• ステータス精度向上 — フォルテ(スキルツリー)の固定ステータスボーナスを反映し、パーティ・実測ダメージの数値がゲーム内パネルにより近くなります。\n"
        "• AIメインアタッカー指定 — パーティビルドで好きなキャラクターをメインアタッカーに直接指定できます(ロールタグに関係なくビルド・評価)。\n"
        "• AI名前識別の改善 — チャットで「チサ」と「熾霞」のような似た名前を正確に区別します。\n"
        "• ピックアップ日程の訂正 — 3.5バナーの切り替え日程を修正しました(7月31日 → 30日)。"
    ),
    "description_zhHans": (
        "已反映鸣潮3.5新内容与易用性改进。\n"
        "• 3.5新声骸 — 将20种声骸和3种新合鸣(羽落空尘之歌·清邪荡煞之心·冥途夜行之灯)加入图鉴·队伍搭配。\n"
        "• 属性准确度提升 — 计入共鸣回路(技能树)的固定属性加成,使队伍·实测伤害数值更接近游戏内面板。\n"
        "• AI主C指定 — 可在队伍搭配中直接将任意角色指定为主C(不受职责标签限制进行配装·评估)。\n"
        "• AI名称识别优化 — 在对话中能准确区分「奇莎」和「炽霞」等相近的名称。\n"
        "• 抽卡日程订正 — 修正了3.5卡池切换日程(7月31日 → 30日)。"
    ),
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
