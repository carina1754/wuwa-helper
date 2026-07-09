from __future__ import annotations

import json

from .database import get_connection
from .models import AiMessage, AiProfile, AiRecommendationRecord, Recommendation


def save_recommendation(record: AiRecommendationRecord) -> AiRecommendationRecord:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_recommendations
            (id, user_id, created_at, profile_json, conversation_json, recommendation_json, title)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                created_at = EXCLUDED.created_at,
                profile_json = EXCLUDED.profile_json,
                conversation_json = EXCLUDED.conversation_json,
                recommendation_json = EXCLUDED.recommendation_json,
                title = EXCLUDED.title
            """,
            (
                record.id,
                record.user_id,
                record.created_at,
                record.profile.model_dump_json(),
                json.dumps([message.model_dump() for message in record.conversation], ensure_ascii=False),
                record.recommendation.model_dump_json(),
                record.title,
            ),
        )
        conn.commit()
    return record


def _row_to_record(row) -> AiRecommendationRecord:
    return AiRecommendationRecord(
        id=row["id"],
        user_id=row.get("user_id"),
        created_at=row["created_at"],
        profile=AiProfile.model_validate_json(row["profile_json"]),
        conversation=[AiMessage.model_validate(item) for item in json.loads(row["conversation_json"])],
        recommendation=Recommendation.model_validate_json(row["recommendation_json"]),
        title=row.get("title"),
    )


def list_recommendations(user_id: str | None = None, limit: int = 20) -> list[AiRecommendationRecord]:
    with get_connection() as conn:
        if user_id:
            rows = conn.execute(
                "SELECT * FROM ai_recommendations WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
                (user_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ai_recommendations ORDER BY created_at DESC LIMIT %s",
                (limit,),
            ).fetchall()
    return [_row_to_record(row) for row in rows]


def get_recommendation(recommendation_id: str) -> AiRecommendationRecord | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM ai_recommendations WHERE id = %s", (recommendation_id,)
        ).fetchone()
    return _row_to_record(row) if row else None


def delete_recommendation(recommendation_id: str) -> bool:
    """저장된 추천 1건 삭제. 실제로 지워졌으면 True."""
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM ai_recommendations WHERE id = %s", (recommendation_id,))
        conn.commit()
        return (cur.rowcount or 0) > 0
