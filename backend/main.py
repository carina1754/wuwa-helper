from __future__ import annotations

import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# backend/.env 를 프로세스 환경에 로드(로컬 LLM 폴백용 LLM_* 등). 없으면 무시.
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src import ai_coach
from src.ai_store import (
    delete_recommendation,
    get_recommendation,
    list_recommendations,
    save_recommendation,
)
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
from src.media import CATALOG_KINDS, cached_catalog_image_path, cached_image_path
from src.models import (
    AiChatRequest,
    AiChatResponse,
    AiRecommendationCreate,
    AiRecommendationRecord,
    GameUpdateSummary,
    PickupBanner,
    PickupScheduleItem,
    SiteUpdateEntry,
)
from src.sim.api import TeamCalcRequest, TeamCalcResponse, team_calculate

app = FastAPI(title="WaWa AI Helper API", version="0.2.0")

default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://wuwahelper.com",
    "https://www.wuwahelper.com",
    "https://wawahelper.com",
    "https://www.wawahelper.com",
]
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", ",".join(default_origins)).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


# --- Catalog / content (static files, no DB) ---------------------------------


@app.get("/pickup-schedule", response_model=list[PickupScheduleItem])
def get_pickup_schedule(year: int | None = None) -> list[PickupScheduleItem]:
    return load_pickup_schedule(year)


@app.get("/updates", response_model=list[GameUpdateSummary])
def get_updates() -> list[GameUpdateSummary]:
    return load_game_updates()


@app.get("/updates/image/{update_id}")
def get_update_image(update_id: str) -> FileResponse:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", update_id):
        raise HTTPException(status_code=404, detail="Update image not found")
    path = cached_image_path(update_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Update image not found")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/sonata-sets")
def get_sonata_sets() -> list[dict]:
    return load_sonata_sets()


@app.get("/codex/resonators")
def get_codex_resonators() -> list[dict]:
    return load_codex_resonators()


@app.get("/codex/weapons")
def get_codex_weapons() -> list[dict]:
    return load_codex_weapons()


@app.get("/codex/echoes")
def get_codex_echoes() -> list[dict]:
    return load_codex_echoes()


@app.get("/pickup-banners", response_model=list[PickupBanner])
def get_pickup_banners() -> list[PickupBanner]:
    return load_pickup_banners()


@app.get("/catalog/image/{kind}/{item_id}")
def get_catalog_image(kind: str, item_id: str) -> FileResponse:
    if kind not in CATALOG_KINDS or not re.fullmatch(r"[A-Za-z0-9_-]+", item_id):
        raise HTTPException(status_code=404, detail="Image not found")
    path = cached_catalog_image_path(kind, item_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/site-updates", response_model=list[SiteUpdateEntry])
def get_site_updates() -> list[SiteUpdateEntry]:
    return load_site_updates()


@app.get("/game-config")
def get_game_config() -> dict:
    return load_game_config()


# --- Party damage sim --------------------------------------------------------


@app.post("/sim/team-calculate", response_model=TeamCalcResponse)
def post_team_calculate(request: TeamCalcRequest) -> TeamCalcResponse:
    """Server-side party damage calc from real builds (our engine)."""
    try:
        return team_calculate(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# --- AI coach (BYO NVIDIA key via headers, local-file history) ----------------


@app.post("/ai/chat", response_model=AiChatResponse)
def post_ai_chat(
    request: AiChatRequest,
    x_llm_key: str | None = Header(default=None),
    x_llm_model: str | None = Header(default=None),
) -> AiChatResponse:
    # 키·모델은 헤더로만 받는다(본문/기록에 절대 안 섞음).
    return ai_coach.chat(request, api_key=x_llm_key, model=x_llm_model)


@app.get("/ai/models")
def get_ai_models(x_llm_key: str | None = Header(default=None)) -> list[str]:
    if not x_llm_key:
        raise HTTPException(status_code=400, detail="NVIDIA API 키가 필요합니다 (X-LLM-Key 헤더).")
    try:
        return ai_coach.list_models(x_llm_key)
    except Exception as exc:  # noqa: BLE001 — 외부 API 실패를 502로 표면화
        raise HTTPException(status_code=502, detail=f"모델 목록 조회 실패: {exc}")


@app.get("/ai/recommendations", response_model=list[AiRecommendationRecord])
def get_ai_recommendations(user_id: str | None = None) -> list[AiRecommendationRecord]:
    return list_recommendations(user_id=user_id)


@app.post("/ai/recommendations", response_model=AiRecommendationRecord)
def post_ai_recommendation(payload: AiRecommendationCreate) -> AiRecommendationRecord:
    record = AiRecommendationRecord(
        id=secrets.token_hex(12),
        user_id=payload.user_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        profile=payload.profile,
        conversation=payload.conversation,
        recommendation=payload.recommendation,
        title=payload.title,
    )
    return save_recommendation(record)


@app.get("/ai/recommendations/{recommendation_id}", response_model=AiRecommendationRecord)
def get_ai_recommendation_detail(recommendation_id: str) -> AiRecommendationRecord:
    record = get_recommendation(recommendation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return record


@app.delete("/ai/recommendations/{recommendation_id}", status_code=204)
def delete_ai_recommendation(recommendation_id: str) -> Response:
    if not delete_recommendation(recommendation_id):
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return Response(status_code=204)


# --- Static frontend (single-process standalone) -----------------------------
# Serve the built Next.js export so one process = whole app. MUST be mounted last
# so the "/" catch-all never shadows an API route above. Absent in dev (frontend
# runs on :3000); present in the packaged build (STATIC_DIR or ./static).
_STATIC_DIR = os.getenv("STATIC_DIR") or str(Path(__file__).resolve().parent / "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
