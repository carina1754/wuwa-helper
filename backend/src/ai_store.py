"""AI 추천 기록 저장소 — 로컬 JSON 파일(무DB, 단일 로컬 유저).

user_id 스코프는 단일 로컬 유저라 무시한다(인자는 하위호환용으로만 유지).
"""
from __future__ import annotations

from . import localstore
from .models import AiRecommendationRecord

_FILE = "ai_recommendations.json"


def _all() -> list[dict]:
    return localstore.read_json(_FILE, [])


def save_recommendation(record: AiRecommendationRecord) -> AiRecommendationRecord:
    items = [r for r in _all() if r.get("id") != record.id]
    items.append(record.model_dump())
    localstore.write_json(_FILE, items)
    return record


def list_recommendations(user_id: str | None = None, limit: int = 20) -> list[AiRecommendationRecord]:
    items = sorted(_all(), key=lambda r: r.get("created_at", ""), reverse=True)
    return [AiRecommendationRecord.model_validate(r) for r in items[:limit]]


def get_recommendation(recommendation_id: str) -> AiRecommendationRecord | None:
    for r in _all():
        if r.get("id") == recommendation_id:
            return AiRecommendationRecord.model_validate(r)
    return None


def delete_recommendation(recommendation_id: str) -> bool:
    items = _all()
    kept = [r for r in items if r.get("id") != recommendation_id]
    if len(kept) == len(items):
        return False
    localstore.write_json(_FILE, kept)
    return True
