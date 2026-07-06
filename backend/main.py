from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.database import init_db
from src.content import load_game_updates, load_pickup_schedule
from src.content_refresh import refresh_pickups_and_updates, start_daily_refresh_worker
from src.evaluator import choose_rule, evaluate_account, evaluate_character, evaluate_echo
from src.export_import import export_all, import_all
from src.history import get_session, list_sessions, save_session
from src.models import (
    AnalysisSession,
    AnalyzeRequest,
    AnalyzeResponse,
    BuildRule,
    CharacterCatalogItem,
    Diagnosis,
    GameUpdateSummary,
    EchoItem,
    PickupScheduleItem,
    VisionExtractionResult,
)
from src.report import generate_report
from src.rules import load_build_rules, load_character_catalog, save_build_rules
from src.vision import extract_from_image

app = FastAPI(title="WuWa AI Coach API", version="0.1.0")

default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
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
start_daily_refresh_worker()


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


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
