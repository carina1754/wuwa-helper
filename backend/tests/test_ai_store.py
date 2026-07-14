from __future__ import annotations

from src import ai_store
from src.models import (
    AiMessage,
    AiProfile,
    AiRecommendationRecord,
    EchoPick,
    Recommendation,
    TeamPick,
    WeaponPick,
)


def _make_record(record_id: str, user_id: str | None) -> AiRecommendationRecord:
    return AiRecommendationRecord(
        id=record_id,
        user_id=user_id,
        created_at="2026-07-08T00:00:00+00:00",
        profile=AiProfile(union_level=45, owned_characters=["능양"], play_style="딜"),
        conversation=[
            AiMessage(role="user", content="딜러 추천해줘"),
            AiMessage(role="assistant", content="능양을 메인 딜러로 추천합니다."),
        ],
        recommendation=Recommendation(
            summary="능양 메인 딜러 빌드",
            team=[
                TeamPick(
                    resonator_id="1104",
                    role="main_dps",
                    reason="응결 메인 딜러",
                    weapon=WeaponPick(id="21010011", alt_ids=["21010012"], reason="예산 대안"),
                    echo=EchoPick(sonata_ids=["s-1"], main_echo_id="60000225", main_stats={"cost4": "속성피해"}),
                    priority=1,
                )
            ],
            upgrade_order=["연각 50까지", "무기 강화"],
        ),
        title="능양 메인 딜러 빌드",
    )


def _cleanup(record_ids: list[str], user_ids: list[str]) -> None:
    # 로컬 파일 스토어(DB 없음) 정리. user_ids 는 무시(FK/유저 테이블 없음).
    for record_id in record_ids:
        ai_store.delete_recommendation(record_id)


def test_save_and_get_roundtrip():
    record = _make_record("test-ai-rec-roundtrip", "test-ai-user-1")
    try:
        ai_store.save_recommendation(record)
        loaded = ai_store.get_recommendation("test-ai-rec-roundtrip")
        assert loaded is not None
        assert loaded.title == "능양 메인 딜러 빌드"
        assert loaded.profile.union_level == 45
        assert loaded.recommendation.team[0].resonator_id == "1104"
        assert loaded.recommendation.team[0].weapon.id == "21010011"
        assert loaded.recommendation.team[0].echo.main_echo_id == "60000225"
        assert len(loaded.conversation) == 2
    finally:
        _cleanup(["test-ai-rec-roundtrip"], ["test-ai-user-1"])


def test_list_returns_all_records_ignoring_user():
    # 무로그인 단일 로컬 유저: user_id 스코프 없음(넣어도 무시). 저장된 건 모두 보인다.
    mine = _make_record("test-ai-rec-mine", "test-ai-user-scope")
    other = _make_record("test-ai-rec-other", "test-ai-user-different")
    try:
        ai_store.save_recommendation(mine)
        ai_store.save_recommendation(other)
        ids = {row.id for row in ai_store.list_recommendations(user_id="test-ai-user-scope")}
        assert "test-ai-rec-mine" in ids
        assert "test-ai-rec-other" in ids  # 스코프 없음 → 다른 user_id 도 보임
    finally:
        _cleanup(["test-ai-rec-mine", "test-ai-rec-other"], [])


def test_save_is_idempotent_upsert():
    record = _make_record("test-ai-rec-upsert", "test-ai-user-upsert")
    try:
        ai_store.save_recommendation(record)
        record.title = "수정된 제목"
        ai_store.save_recommendation(record)
        loaded = ai_store.get_recommendation("test-ai-rec-upsert")
        assert loaded is not None
        assert loaded.title == "수정된 제목"
        rows = ai_store.list_recommendations(user_id="test-ai-user-upsert")
        assert len([r for r in rows if r.id == "test-ai-rec-upsert"]) == 1
    finally:
        _cleanup(["test-ai-rec-upsert"], ["test-ai-user-upsert"])
