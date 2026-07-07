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
    "3.3": {
        "summary_ko": (
            "「별바다의 끝에서 닿은 메아리」 3.3 버전에서는 신규 5성 공명자 히유키와 "
            "데니아가 등장하고, 신규 지역 「어둠의 평원」과 조수 임무 제3장 제5막이 "
            "열립니다. 2026년 4월 30일 점검 후 적용됩니다."
        ),
        "highlights_ko": [
            "신규 5성 히유키(응결·직검) — 공명 해방 피해 메인 딜러",
            "신규 5성 데니아(용융·증폭기) — 빠른 협주·조화도 파괴 서포터",
            "신규 지역 「어둠의 평원」, 조수 임무 제3장 제5막 「어젯밤의 뭇별들」",
            "신규 무기 서린 불꽃(직검)·위조된 작은별(증폭기), 신규 화음 세트 2종",
            "업데이트 점검: 2026년 4월 30일 05:00~12:00 (KST)",
        ],
    },
    "3.2": {
        "summary_ko": (
            "「그림자 속에서 밝혀진 결심」 3.2 버전에서는 신규 5성 공명자 시그리카가 "
            "등장하고, 조수 임무 제3장 제4막과 신규 고난도 주기 도전 「종말 매트릭스」가 "
            "추가됩니다. 2026년 3월 19일 점검 후 적용됩니다."
        ),
        "highlights_ko": [
            "신규 5성 시그리카(기류·권갑) — 에코 어빌리티 피해 메인 딜러",
            "신규 무기 「솔스원의 해석」(권갑)",
            "조수 임무 제3장 제4막 「그림자 아래 떨어지지 않는 황금」",
            "신규 고난도 주기 도전 「종말 매트릭스」",
            "신규 이벤트 「리듬을 따라 출항」·「황야의 기사」, 탐사 바이크·에코 필터 편의성 개선",
            "업데이트 점검: 2026년 3월 19일 05:00~12:00 (KST)",
        ],
    },
    "3.1": {
        "summary_ko": (
            "「눈 속에 있는 그대에게」 3.1 버전에서는 신규 5성 공명자 에이메스와 "
            "루크·헤르센이 등장하고, 신규 지역 「로야 빙원·빙원 지표면」과 조수 임무 "
            "제3장 제3막이 열립니다. 2026년 2월 5일 점검 후 적용됩니다."
        ),
        "highlights_ko": [
            "신규 5성 에이메스(용융·직검) — 공명 해방 피해 메인 딜러",
            "신규 5성 루크·헤르센(회절·권갑) — 일반 공격 메인 딜러",
            "신규 지역 「로야 빙원·빙원 지표면」, 조수 임무 제3장 제3막 「먼 길을 떠나는 별」",
            "신규 무기 영원한 샛별(직검)·한낮의 의지(권갑), 신규 화음 세트 3종",
            "신규 이벤트 「은하가 쏟아지는 사이」·「극지 추적」·「영광의 언덕 돌아온 격투」",
            "업데이트 점검: 2026년 2월 5일 05:00~12:00 (KST)",
        ],
    },
    "3.0": {
        "summary_ko": (
            "「별하늘을 보기 위해 태어난 우리들」 3.0 버전에서는 신규 지역 「라하이 로이」와 "
            "스타토치 아카데미가 개방되고 조수 임무 제3장이 시작됩니다. 신규 5성 공명자 "
            "린네와 모니에가 등장하며, 지역 탐험용 「탐사 바이크」가 추가됩니다. "
            "2025년 12월 25일 점검 후 적용됩니다."
        ),
        "highlights_ko": [
            "신규 5성 린네(회절·권총) — 빠른 협주 딜러, 일반 공격·공명 해방 피해",
            "신규 5성 모니에(용융·대검) — 생존·치료형 서포터",
            "신규 지역 「라하이 로이」 + 스타토치 아카데미, 조수 임무 제3장 개막",
            "신규 탐색 도구 「탐사 바이크」 — 주행·외형 커스텀·확장 모듈",
            "신규 무기 스펙트럼 블래스터(권총)·별하늘 연산 측정기(대검), 신규 화음 세트 3종",
            "업데이트 점검: 2025년 12월 25일 05:00~12:00 (KST)",
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
