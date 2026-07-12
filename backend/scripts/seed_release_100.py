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
    "title_en": "1.0.0 Official Release",
    "title_ja": "1.0.0 正式版リリース",
    "title_zhHans": "1.0.0 正式版发布",
    "description_en": (
        "WuWa Helper has reached its official release. It brings together all the updates so far to provide the features below reliably.\n"
        "• Party damage calculation — place 3 Resonators and the server engine calculates total party damage and contributions. Supports automatic team-shared buffs, Resonance Chain (Sequence) reflection, a full-uptime option, and enemy-condition settings.\n"
        "• Codex — provides info on all Resonators, weapons, and echoes, along with skill multipliers (per-level totals).\n"
        "• Banner schedule — see the pickup banner schedule for each version at a glance.\n"
        "• Measured damage — upload a character screenshot and it calculates absolute damage reflecting your actual echo sub-stats.\n"
        "• AI Build — tell it your owned characters and goals, and the AI recommends builds and parties and saves them as records. You can search and pick characters by icon, and enter your play style freely.\n"
        "• User guide — the ? icon at the top explains how to use every feature, with screenshots.\n"
        "• Security & performance — hardened protection for the admin API and greatly reduced initial load size.\n"
        "Thank you for using it. Please leave improvement requests and bug reports on Discord."
    ),
    "description_ja": (
        "鳴潮ヘルパーが正式版になりました。これまでのアップデートをまとめ、以下の機能を安定して提供します。\n"
        "• パーティダメージ計算 — 共鳴者3人を編成すると、サーバーエンジンがパーティ全体のダメージと貢献度を計算します。チーム共有バフの自動適用、共鳴チェーン(シーケンス)反映、フルアップタイムオプション、敵条件設定に対応します。\n"
        "• 図鑑 — 全共鳴者・武器・エコー情報とスキル倍率(レベル別合計)を提供します。\n"
        "• ピックアップ日程 — バージョンごとのピックアップバナー日程を一目で確認できます。\n"
        "• 実測ダメージ — キャラクター情報のスクリーンショットをアップロードすると、実際のエコーサブステータスを反映した絶対ダメージを計算します。\n"
        "• AIビルド — 所持キャラクターと目標を伝えると、AIがビルドとパーティを推薦し、記録として保存します。キャラクターはアイコンで検索・選択でき、プレイスタイルは自由に入力できます。\n"
        "• 利用ガイド — 上部の?アイコンから、スクリーンショット付きで全機能の使い方を確認できます。\n"
        "• セキュリティ・パフォーマンス — 管理用APIの保護を強化し、初回読み込み容量を大幅に削減しました。\n"
        "ご利用ありがとうございます。改善のご要望やバグ報告はDiscordへお寄せください。"
    ),
    "description_zhHans": (
        "鸣潮助手已进入正式版。它汇集了此前的所有更新,稳定地提供以下功能。\n"
        "• 队伍伤害计算 — 编入3名共鸣者后,服务器引擎会计算队伍整体伤害与贡献度。支持队伍共享增益自动生效、共鸣链(序列)反映、满轴选项及敌人条件设置。\n"
        "• 图鉴 — 提供全部共鸣者·武器·声骸信息以及技能倍率(按等级汇总)。\n"
        "• 抽卡日程 — 一目了然地查看各版本的抽卡卡池日程。\n"
        "• 实测伤害 — 上传角色信息截图,即可计算反映实际声骸副属性的绝对伤害。\n"
        "• AI搭配 — 告知持有角色与目标后,AI会推荐配装与队伍并保存为记录。角色可通过图标搜索·选择,游玩风格可自由输入。\n"
        "• 使用指南 — 通过顶部的?图标,可查看带截图的全部功能使用方法。\n"
        "• 安全·性能 — 强化了管理用API的保护,并大幅减小了首次加载体积。\n"
        "感谢使用。改进建议与漏洞反馈请留言至Discord。"
    ),
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
