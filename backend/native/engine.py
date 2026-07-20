"""엔진 브리지 — Qt가 부르는 단일 데이터/계산 진입점 (HTTP 없음).

카탈로그/콘텐츠 로더는 src 에서 그대로 재노출(이미 lru_cache).
모든 딜/스탯 숫자는 권위 엔진 team_calculate 하나로 계산(클라 근사 math 미포팅).
AI 는 설정파일의 BYO NVIDIA 키를 주입해 호출.
"""
from __future__ import annotations

from src import ai_coach, ai_store
from src.catalog import (
    load_codex_echoes,
    load_codex_resonators,
    load_codex_weapons,
    load_pickup_banners,
    load_sonata_sets,
)
from src.content import (
    load_game_config,
    load_game_updates,
    load_pickup_schedule,
    load_site_updates,
)
from src.models import AiChatRequest, AiProfile, AiRecommendationRecord, Recommendation, TeamPick
from src.sim.api import EchoIn, MemberIn, OptsIn, SubIn, TeamCalcRequest, team_calculate

from . import settings

# --- Catalog / content (thin re-export; underlying loaders are cached) --------
resonators = load_codex_resonators
weapons = load_codex_weapons
echoes = load_codex_echoes
sonata_sets = load_sonata_sets
pickup_banners = load_pickup_banners
pickup_schedule = load_pickup_schedule
game_updates = load_game_updates
site_updates = load_site_updates
game_config = load_game_config

# re-export sim input models so tabs build requests without reaching into src
__all__ = [
    "resonators", "weapons", "echoes", "sonata_sets", "pickup_banners",
    "pickup_schedule", "game_updates", "site_updates", "game_config",
    "MemberIn", "EchoIn", "SubIn", "OptsIn", "TeamCalcRequest",
    "calculate", "member_preview", "ai_chat", "ai_models",
    "ai_list", "ai_save", "ai_get", "ai_delete", "AiChatRequest", "AiRecommendationRecord",
    "AiProfile", "Recommendation", "TeamPick",
]


def calculate(request: TeamCalcRequest):
    """Authoritative party damage calc. Raises KeyError on unknown reso_id."""
    return team_calculate(request)


def member_preview(member: MemberIn, opts: OptsIn | None = None):
    """One member's final stats + skill damage (codex detail / build editor)."""
    req = TeamCalcRequest(members=[member], opts=opts or OptsIn())
    return team_calculate(req).members[0]


# --- AI (BYO NVIDIA key from local settings file) ----------------------------
def ai_chat(request: AiChatRequest):
    s = settings.load()
    return ai_coach.chat(request, api_key=s.get("nvidia_key") or None, model=s.get("model") or None)


def ai_models() -> list[str]:
    """List chat models. Raises ValueError if no key set."""
    key = settings.load().get("nvidia_key")
    if not key:
        raise ValueError("NVIDIA API 키가 필요합니다 (설정 탭).")
    return ai_coach.list_models(key)


# --- AI recommendation history (local JSON store) ----------------------------
ai_list = ai_store.list_recommendations
ai_save = ai_store.save_recommendation
ai_get = ai_store.get_recommendation
ai_delete = ai_store.delete_recommendation
