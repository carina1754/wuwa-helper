from __future__ import annotations

import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# backend/.env 를 프로세스 환경에 로드한다. 이게 없으면 INTERNAL_API_SECRET 등이
# os.getenv 로 안 잡혀 sync-user 가 401 → users 테이블이 비고 → 저장이 FK 위반으로 500난다.
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import Depends, FastAPI, File, Header, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.database import init_db
from src.content import load_game_config, load_game_updates, load_pickup_schedule, load_site_updates
from src.content_refresh import refresh_pickups_and_updates, start_daily_refresh_worker
from src.curated_updates import apply_curated_update_summaries
from src.evaluator import choose_rule, evaluate_account, evaluate_character, evaluate_echo
from src.export_import import export_all, import_all
from src.history import get_session, list_sessions, save_session
from src import ai_coach
from src.ai_store import delete_recommendation, get_recommendation, list_recommendations, save_recommendation
from src.catalog import (
    load_codex_echoes,
    load_codex_resonators,
    load_codex_weapons,
    load_pickup_banners,
    load_sonata_sets,
)
from src.media import CATALOG_KINDS, cached_catalog_image_path, cached_image_path
from src.models import (
    AiChatRequest,
    AiChatResponse,
    AiRecommendationCreate,
    AiRecommendationRecord,
    AuthUserSyncRequest,
    AnalysisSession,
    AnalyzeRequest,
    AnalyzeResponse,
    BuildRule,
    Diagnosis,
    GameUpdateSummary,
    PickupBanner,
    EchoItem,
    PickupScheduleItem,
    SiteUpdateEntry,
    VisionExtractionResult,
    UserRecord,
)
from src.report import generate_report
from src.rules import load_build_rules, save_build_rules
from src.sim.api import (
    SnapshotDamageRequest,
    SnapshotDamageResponse,
    TeamCalcRequest,
    TeamCalcResponse,
    snapshot_damage_api,
    team_calculate,
)
from src.users import sync_user
from src.vision import extract_from_image

app = FastAPI(title="WaWa AI Helper API", version="0.1.0")

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

# Test clients and short-lived scripts do not always enter FastAPI lifespan.
init_db()
apply_curated_update_summaries()
start_daily_refresh_worker()


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


def require_internal_secret(x_internal_secret: str | None = Header(default=None)) -> None:
    expected = os.getenv("INTERNAL_API_SECRET")
    if not expected or not x_internal_secret or not secrets.compare_digest(x_internal_secret, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing internal API secret")


@app.post("/auth/sync-user", response_model=UserRecord, dependencies=[Depends(require_internal_secret)])
def post_auth_sync_user(payload: AuthUserSyncRequest) -> UserRecord:
    return sync_user(payload)

@app.get("/rules", response_model=list[BuildRule])
def get_rules() -> list[BuildRule]:
    return load_build_rules()


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


@app.post("/sim/team-calculate", response_model=TeamCalcResponse)
def post_team_calculate(request: TeamCalcRequest) -> TeamCalcResponse:
    """Server-side party damage calc from real builds (our engine, not phro assumptions)."""
    try:
        return team_calculate(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/sim/snapshot-damage", response_model=SnapshotDamageResponse)
def post_snapshot_damage(request: SnapshotDamageRequest) -> SnapshotDamageResponse:
    """Absolute damage from a real-account OCR snapshot — our '내 실제 빌드 기준' differentiator."""
    try:
        return snapshot_damage_api(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/content/refresh")
def post_content_refresh() -> dict[str, object]:
    return refresh_pickups_and_updates(force=True)


@app.post("/rules", response_model=list[BuildRule])
def post_rules(rules: list[BuildRule]) -> list[BuildRule]:
    return save_build_rules(rules)


@app.post("/vision/extract", response_model=VisionExtractionResult)
async def post_vision_extract(file: UploadFile = File(...)) -> VisionExtractionResult:
    image_bytes = await file.read()
    return extract_from_image(image_bytes, file.filename)


@app.post("/analyze/echo", response_model=Diagnosis)
def post_analyze_echo(echo: EchoItem) -> Diagnosis:
    rule = load_build_rules()[0]
    return evaluate_echo(echo, rule)


@app.post("/analyze/character", response_model=AnalyzeResponse)
def post_analyze_character(request: AnalyzeRequest) -> AnalyzeResponse:
    rules = load_build_rules()
    role = request.snapshot.role or request.fallback_role
    rule = choose_rule(request.snapshot.character_name, rules, role)
    diagnoses = evaluate_character(request.snapshot, rule)
    report = generate_report(request.snapshot, diagnoses)
    return AnalyzeResponse(snapshot=request.snapshot, diagnoses=diagnoses, report=report)


@app.post("/analyze/account", response_model=list[Diagnosis])
def post_analyze_account(profile: dict[str, Any]) -> list[Diagnosis]:
    return evaluate_account(profile)


@app.post("/report")
def post_report(payload: AnalyzeResponse) -> dict[str, str]:
    return {"report": generate_report(payload.snapshot, payload.diagnoses)}


@app.get("/history", response_model=list[AnalysisSession])
def get_history() -> list[AnalysisSession]:
    return list_sessions()


@app.post("/history", response_model=AnalysisSession)
def post_history(session: AnalysisSession) -> AnalysisSession:
    return save_session(session)


@app.get("/history/{session_id}", response_model=AnalysisSession)
def get_history_detail(session_id: str) -> AnalysisSession:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Analysis session not found")
    return session


@app.post("/ai/chat", response_model=AiChatResponse)
def post_ai_chat(request: AiChatRequest) -> AiChatResponse:
    return ai_coach.chat(request)


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


@app.get("/export")
def get_export() -> dict[str, Any]:
    return export_all()


@app.post("/import")
def post_import(payload: dict[str, Any]) -> dict[str, int]:
    return import_all(payload)
