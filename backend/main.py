from __future__ import annotations

import os
import re
import secrets
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.database import init_db
from src.content import load_game_updates, load_pickup_schedule, load_site_updates
from src.content_refresh import refresh_pickups_and_updates, start_daily_refresh_worker
from src.curated_updates import apply_curated_update_summaries
from src.evaluator import choose_rule, evaluate_account, evaluate_character, evaluate_echo
from src.export_import import export_all, import_all
from src.history import get_session, list_sessions, save_session
from src.catalog import (
    load_character_kits,
    load_echoes,
    load_sonata_sets,
    load_weapon_catalog,
)
from src.media import CATALOG_KINDS, cached_catalog_image_path, cached_image_path
from src.models import (
    AuthUserSyncRequest,
    AnalysisSession,
    AnalyzeRequest,
    AnalyzeResponse,
    BuildRule,
    CharacterCatalogItem,
    Diagnosis,
    GameUpdateSummary,
    WeaponCatalogItem,
    EchoItem,
    PickupScheduleItem,
    SiteUpdateEntry,
    VisionExtractionResult,
    UserRecord,
)
from src.report import generate_report
from src.rules import load_build_rules, load_character_catalog, save_build_rules
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


@app.get("/characters", response_model=list[CharacterCatalogItem])
def get_characters() -> list[CharacterCatalogItem]:
    return load_character_catalog()


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


@app.get("/weapons", response_model=list[WeaponCatalogItem])
def get_weapons() -> list[WeaponCatalogItem]:
    return load_weapon_catalog()


@app.get("/character-kits")
def get_character_kits() -> list[dict]:
    return load_character_kits()


@app.get("/echoes")
def get_echoes() -> list[dict]:
    return load_echoes()


@app.get("/sonata-sets")
def get_sonata_sets() -> list[dict]:
    return load_sonata_sets()


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


@app.get("/export")
def get_export() -> dict[str, Any]:
    return export_all()


@app.post("/import")
def post_import(payload: dict[str, Any]) -> dict[str, int]:
    return import_all(payload)
