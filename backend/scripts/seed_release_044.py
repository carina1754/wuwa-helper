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
    "title_en": "0.4.4 Update",
    "title_ja": "0.4.4 アップデート",
    "title_zhHans": "0.4.4 更新",
    "description_en": (
        "• Added a 'full uptime' option to party damage calculation (on by default). When on, the conditional buffs from Resonance Chain (Sequence), weapons, and traits are applied on an ideal rotation basis, so the result is close to real maximum damage.\n"
        "• Previously these conditional effects were omitted, so total damage showed much lower than reality. In particular, the per-stage damage increase of the Resonance Chain (Sequence) is now reflected correctly, making calculations accurate for characters whose damage rises sharply at higher sequences.\n"
        "• If you want a conservative figure closer to a real account, turn 'full uptime' off to calculate with always-on buffs only."
    ),
    "description_ja": (
        "• パーティダメージ計算に「フルアップタイム」オプションを追加しました(デフォルトON)。ONの場合、共鳴チェーン(シーケンス)・武器・特性の条件付きバフを理想的なローテーション基準で反映し、実際の最大ダメージに近づけて計算します。\n"
        "• 以前はこれらの条件付き効果が抜けており、総ダメージが実際よりも大きく低く表示されていました。特に共鳴チェーン(シーケンス)の段階別ダメージ増加が正常に反映され、上位シーケンスでダメージが大きく伸びるキャラクターの計算が正確になりました。\n"
        "• 実際のアカウントに近い保守的な数値を見たい場合は、「フルアップタイム」をOFFにして常時発動バフのみで計算できます。"
    ),
    "description_zhHans": (
        "• 在队伍伤害计算中新增「满轴」选项(默认开启)。开启时,会以理想循环为基准计入共鸣链(序列)·武器·特性的条件类增益,使结果更接近实际最大伤害。\n"
        "• 此前由于缺少这些条件类效果,总伤害显示得远低于实际。尤其是共鸣链(序列)的分阶段伤害提升现已正常计入,使高序列下伤害大幅提升的角色的计算更加准确。\n"
        "• 若想查看更接近真实账号的保守数值,可关闭「满轴」,仅以常驻增益进行计算。"
    ),
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
