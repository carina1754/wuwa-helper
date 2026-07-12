"""Seed the 0.4.0 site-update (공지사항) entry. Idempotent (upsert by id).

Usage: uv run python scripts/seed_release_040.py   (targets DATABASE_URL)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import get_connection  # noqa: E402

ENTRY = {
    "id": "release-0-4-0-2026-07-09",
    "date": "2026-07-09",
    "version": "0.4.0",
    "title_ko": "0.4.0 업데이트",
    "title_en": "0.4.0 Update",
    "title_ja": "0.4.0 アップデート",
    "title_zhHans": "0.4.0 更新",
    "description_en": (
        "• AI Build: get conversational recommendations for characters, weapons, echoes, sonatas, and upgrade order. Upload a screenshot and your owned characters are recognized automatically.\n"
        "• Party damage index: computes the relative damage index of a recommended lineup and shows each character's contribution (%). It's a comparison figure based on standard-build assumptions.\n"
        "• Save & delete records: save recommendations you like to the 'History' tab and delete the ones you don't need.\n"
        "• UI cleanup: removed the in-progress dashboard and renamed the service to 'WuWa Helper'."
    ),
    "description_ja": (
        "• AIビルド:キャラクター・武器・エコー・ソナタと育成順序を対話形式で提案します。スクリーンショットをアップロードすると所持キャラクターを自動認識します。\n"
        "• パーティダメージ指数:推薦編成の相対ダメージ指数を計算し、キャラクターごとの貢献度(%)とともに表示します。標準ビルドを前提とした比較用の数値です。\n"
        "• 記録の保存・削除:気に入った推薦を「履歴」タブに保存し、不要な記録は削除できます。\n"
        "• 画面整理:準備中だったダッシュボードを整理し、サービス名を「鳴潮ヘルパー」に変更しました。"
    ),
    "description_zhHans": (
        "• AI搭配:以对话形式推荐角色·武器·声骸·合鸣及养成顺序。上传截图即可自动识别持有角色。\n"
        "• 队伍伤害指数:计算推荐阵容的相对伤害指数,并显示各角色的贡献度(%)。这是基于标准配装假设的对比数值。\n"
        "• 记录保存·删除:可将喜欢的推荐保存到「记录」标签页,并删除不需要的记录。\n"
        "• 界面整理:整理了筹备中的仪表盘,并将服务名称更改为「鸣潮助手」。"
    ),
    "description_ko": (
        "• AI 빌딩: 대화형으로 캐릭터·무기·에코·소나타와 업그레이드 순서를 추천받을 수 있습니다. 스크린샷을 올리면 보유 캐릭터를 자동으로 인식합니다.\n"
        "• 파티 딜 지수: 추천 조합의 상대 딜 지수를 계산해 캐릭터별 기여도(%)와 함께 보여줍니다. 표준 빌드 가정 기반의 비교용 수치입니다.\n"
        "• 기록 저장·삭제: 마음에 드는 추천을 '기록' 탭에 저장하고, 필요 없는 기록은 삭제할 수 있습니다.\n"
        "• 화면 정리: 준비 중이던 대시보드를 정리하고 서비스 이름을 '띵조 AI'로 변경했습니다."
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
