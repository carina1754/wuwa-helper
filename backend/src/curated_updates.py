from __future__ import annotations

import json

from .database import get_connection

# Authored Korean summaries per game version. This module is the source of
# truth so the text survives DB resets and deploys with the code;
# apply_curated_update_summaries() writes it into the game_updates rows that
# the refresh discovers. Extend this dict when a new version's article ships
# (see Task 10 in the plan). NOT a full-dataset seed — only editorial text.
CURATED_UPDATE_SUMMARIES: dict[str, dict] = {
    "3.4": {
        "summary_ko": (
            "「선택하지 않은 꿈」 3.4 버전에서는 사이버펑크: 엣지러너 콜라보가 진행되어 "
            "5성 공명자 루시와 레베카가 등장하고, 신규 5성 공명자 루실라가 추가됩니다. "
            "2026년 6월 8일 점검 후 적용됩니다."
        ),
        "highlights_ko": [
            "콜라보 5성 루시(회절·권총) — 메인 딜러, 강공격/일반 공격 특화",
            "콜라보 5성 레베카(전도·권총) — 빠른 협주, 조화도 파괴 증폭",
            "신규 5성 루실라(응결·증폭기) — 스타토치 아카데미 교장",
            "업데이트 점검: 2026년 6월 8일 05:00~12:00 (KST)",
        ],
    },
}


def apply_curated_update_summaries() -> int:
    """Write authored summaries into matching game_updates rows. Idempotent.

    Matches rows by version. Returns the number of rows actually changed
    (0 when everything already matches).
    """
    updated = 0
    with get_connection() as conn:
        for version, payload in CURATED_UPDATE_SUMMARIES.items():
            row = conn.execute(
                "SELECT id, data_json FROM game_updates WHERE version = %s ORDER BY id LIMIT 1",
                (version,),
            ).fetchone()
            if row is None:
                continue
            data = json.loads(row["data_json"])
            if (
                data.get("summary_ko") == payload["summary_ko"]
                and data.get("highlights_ko") == payload["highlights_ko"]
            ):
                continue
            data["summary_ko"] = payload["summary_ko"]
            data["highlights_ko"] = payload["highlights_ko"]
            conn.execute(
                "UPDATE game_updates SET data_json = %s, updated_at = now() WHERE id = %s",
                (json.dumps(data, ensure_ascii=False), row["id"]),
            )
            updated += 1
        conn.commit()
    return updated
