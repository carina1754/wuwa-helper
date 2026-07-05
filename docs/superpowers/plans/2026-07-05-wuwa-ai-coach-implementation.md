# WuWa AI Coach MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the WuWa AI Coach full-stack MVP with FastAPI, SQLite, GPT Vision/mock extraction, rule-based diagnosis, local reporting, history, export/import, and a Next.js tool UI.

**Architecture:** The backend owns the typed domain model, extraction, rules, evaluation, reporting, and persistence. The frontend is a tabbed single-page Next.js app that calls backend APIs and keeps the active analysis editable. The MVP must be fully usable without an OpenAI API key by using mock extraction data.

**Tech Stack:** Python 3.10+, uv-managed `.venv`, FastAPI, Uvicorn, Pydantic, SQLite, OpenAI API, Next.js, React, TypeScript, Tailwind CSS.

## Global Constraints

- Repository path is `C:\Users\JungSu\Desktop\wawa-ai-coach`.
- Repository folder stays `wawa-ai-coach`; product title is `WuWa AI Coach`.
- Python environment must be created with `uv venv`.
- Backend dependencies must be managed with `backend/pyproject.toml`, `uv.lock`, `uv add`, and `uv add --dev`.
- Missing `OPENAI_API_KEY` must use mock extraction and must not crash the server.
- Uploaded images are not stored by default.
- The app must show that it is a non-official fan tool.
- No official game assets, icons, or bundled game images.
- No SAM3/DINOv3 implementation beyond placeholder adapter interfaces.
- No OCR dependency in the MVP path.
- First screen must be the actual app, not a landing page.

---

## File Structure

Create or modify these files:

- `.gitignore`: ignore Python/Node build artifacts, local env files, local SQLite DB, uploaded temp files, and caches.
- `README.md`: setup, uv venv and uv add commands, backend/frontend run commands, mock mode, rule editing, export/import, legal notice.
- `backend/pyproject.toml`: uv-managed FastAPI backend project metadata and dependencies.
- `backend/uv.lock`: uv lockfile.
- `backend/main.py`: FastAPI app and HTTP routes.
- `backend/data/build_rules.json`: seed build rules.
- `backend/data/team_rules.json`: seed team rules.
- `backend/data/sample_extraction.json`: mock vision result.
- `backend/tests/test_api.py`: backend API behavior tests.
- `backend/tests/test_evaluator.py`: evaluator tests.
- `backend/src/__init__.py`: package marker.
- `backend/src/models.py`: Pydantic models shared by backend modules.
- `backend/src/database.py`: SQLite connection and schema creation.
- `backend/src/rules.py`: JSON rule loading and saving.
- `backend/src/parser.py`: model output JSON extraction and normalization helpers.
- `backend/src/vision.py`: mock/OpenAI vision extraction.
- `backend/src/evaluator.py`: echo, character, account, and team scoring.
- `backend/src/report.py`: local and optional OpenAI report generation.
- `backend/src/history.py`: analysis session persistence.
- `backend/src/export_import.py`: JSON export/import service.
- `backend/src/optional_ocr.py`: OCR placeholder interface.
- `backend/src/optional_local_vision.py`: local vision placeholder interface.
- `frontend/package.json`: scripts and dependencies.
- `frontend/next.config.ts`: Next.js config.
- `frontend/tsconfig.json`: TypeScript config.
- `frontend/postcss.config.mjs`: Tailwind/PostCSS config.
- `frontend/eslint.config.mjs`: lint config.
- `frontend/src/app/globals.css`: Tailwind imports and visual system.
- `frontend/src/app/layout.tsx`: root metadata and app shell wrapper.
- `frontend/src/app/page.tsx`: page-level app entry.
- `frontend/src/lib/types.ts`: TypeScript mirror of backend models.
- `frontend/src/lib/constants.ts`: roles, tabs, empty snapshot, API defaults.
- `frontend/src/lib/api.ts`: fetch client.
- `frontend/src/components/AppShell.tsx`: tab navigation and header.
- `frontend/src/components/Dashboard.tsx`: recent summary.
- `frontend/src/components/ScreenshotAnalyzer.tsx`: main end-to-end flow.
- `frontend/src/components/ImageUploader.tsx`: upload and preview.
- `frontend/src/components/ExtractionPanel.tsx`: JSON/raw text display.
- `frontend/src/components/EchoEditor.tsx`: five echo editors.
- `frontend/src/components/DiagnosisResult.tsx`: diagnosis cards and report.
- `frontend/src/components/CharacterPlanner.tsx`: MVP account planning panel.
- `frontend/src/components/TeamBuilder.tsx`: MVP team recommendation panel.
- `frontend/src/components/RulesManager.tsx`: rules JSON editor.
- `frontend/src/components/HistoryPanel.tsx`: session list/detail panel.
- `frontend/src/components/SettingsPanel.tsx`: API guidance and import/export.

---

### Task 1: Backend Skeleton, Models, uv Project, and Health

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/uv.lock`
- Create: `backend/main.py`
- Create: `backend/src/__init__.py`
- Create: `backend/src/models.py`
- Create: `backend/tests/test_api.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `app: FastAPI` in `backend/main.py`
- Produces: Pydantic models `StatBlock`, `SubStat`, `EchoItem`, `WeaponState`, `CharacterSnapshot`, `VisionExtractionResult`, `BuildRule`, `TeamRule`, `Diagnosis`, `AnalysisSession`, `AnalyzeRequest`, `AnalyzeResponse`
- Produces: `GET /health -> {"ok": true}`

- [ ] **Step 1: Initialize uv backend project, add dependencies, and add ignore rules**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach
New-Item -ItemType Directory -Force backend
cd backend
uv init --bare --name wuwa-ai-coach-backend --no-pin-python --no-workspace
uv venv
uv add "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0" "pydantic>=2.8.0" "python-multipart>=0.0.9" "openai>=1.40.0"
uv add --dev "pytest>=8.2.0" "httpx>=0.27.0"
```

Expected: `backend/pyproject.toml`, `backend/uv.lock`, and `backend/.venv/` exist. Commit `pyproject.toml` and `uv.lock`; do not commit `.venv/`.

Create or update `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
node_modules/
.next/
out/
dist/
build/
*.tsbuildinfo
*.db
*.sqlite
*.sqlite3
uploads/
```

- [ ] **Step 2: Write the failing health test**

Create `backend/tests/test_api.py`:

```python
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
```

- [ ] **Step 3: Run test to verify it fails before implementation**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv venv
uv run pytest tests/test_api.py::test_health_returns_ok -v
```

Expected: FAIL because `main.py` or `app` is not implemented yet.

- [ ] **Step 4: Implement models and health route**

Create `backend/src/__init__.py` as an empty package marker.

Create `backend/src/models.py`:

```python
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["main_dps", "sub_dps", "support", "healer"]
Grade = Literal["excellent", "keep", "upgrade", "hold", "replace", "discard"]
ScreenType = Literal["character_status", "echo_detail", "weapon_detail", "inventory", "team", "unknown"]


class StatBlock(BaseModel):
    hp: str | None = None
    atk: str | None = None
    defense: str | None = None
    crit_rate: str | None = None
    crit_dmg: str | None = None
    energy_regen: str | None = None
    element_dmg_bonus: str | None = None
    healing_bonus: str | None = None


class SubStat(BaseModel):
    name: str | None = None
    value: str | None = None


class EchoItem(BaseModel):
    name: str | None = None
    slot: str | None = None
    set_name: str | None = None
    cost: int | None = None
    level: int | None = None
    main_stat: str | None = None
    sub_stats: list[SubStat] = Field(default_factory=list)


class WeaponState(BaseModel):
    name: str | None = None
    level: int | None = None
    rank: int | None = None
    main_stat: str | None = None


class CharacterSnapshot(BaseModel):
    character_name: str | None = None
    character_level: int | None = None
    role: Role | None = None
    weapon: WeaponState | None = None
    stats: StatBlock = Field(default_factory=StatBlock)
    echoes: list[EchoItem] = Field(default_factory=list)
    raw_text: str = ""


class VisionExtractionResult(BaseModel):
    screen_type: ScreenType = "unknown"
    snapshot: CharacterSnapshot = Field(default_factory=CharacterSnapshot)
    uncertain_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float | None = None
    raw_model_output: str | None = None


class BuildRule(BaseModel):
    character_name: str
    role: Role
    recommended_sets: list[str]
    priority_stats: list[str]
    useful_sub_stats: list[str]
    bad_sub_stats: list[str]
    recommended_weapons: list[str] = Field(default_factory=list)
    notes: str | None = None
    source_links: list[str] = Field(default_factory=list)
    game_version: str | None = None


class TeamRule(BaseModel):
    name: str
    core_character: str
    recommended_teammates: list[str]
    notes: str | None = None


class Diagnosis(BaseModel):
    target_type: Literal["echo", "character", "account", "team"]
    target_name: str | None = None
    grade: Grade
    score: int
    reasons: list[str]
    recommended_actions: list[str]


class AnalysisSession(BaseModel):
    id: str
    created_at: str
    image_filename: str | None = None
    extraction: VisionExtractionResult
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    report: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyzeRequest(BaseModel):
    snapshot: CharacterSnapshot
    fallback_role: Role = "main_dps"


class AnalyzeResponse(BaseModel):
    snapshot: CharacterSnapshot
    diagnoses: list[Diagnosis]
    report: str
```

Create `backend/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="WuWa AI Coach API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest tests/test_api.py::test_health_returns_ok -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach
git add .gitignore backend
git commit -m "feat: add backend skeleton and models"
```

---

### Task 2: SQLite, Rules, History, and Export/Import Services

**Files:**
- Create: `backend/src/database.py`
- Create: `backend/src/rules.py`
- Create: `backend/src/history.py`
- Create: `backend/src/export_import.py`
- Create: `backend/data/build_rules.json`
- Create: `backend/data/team_rules.json`
- Modify: `backend/main.py`
- Modify: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: `BuildRule`, `AnalysisSession`
- Produces: `init_db() -> None`
- Produces: `load_build_rules(path: Path | None = None) -> list[BuildRule]`
- Produces: `save_build_rules(rules: list[BuildRule], path: Path | None = None) -> list[BuildRule]`
- Produces: `save_session(session: AnalysisSession) -> AnalysisSession`
- Produces: `list_sessions(limit: int = 20) -> list[AnalysisSession]`
- Produces: `get_session(session_id: str) -> AnalysisSession | None`
- Produces: `export_all() -> dict[str, Any]`
- Produces: `import_all(payload: dict[str, Any]) -> dict[str, int]`

- [ ] **Step 1: Extend API tests for rules and history**

Append to `backend/tests/test_api.py`:

```python
from src.models import AnalysisSession, VisionExtractionResult


def test_rules_endpoint_returns_seed_rules():
    response = client.get("/rules")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(rule["character_name"] == "default_main_dps" for rule in data)


def test_history_round_trip():
    session = AnalysisSession(
        id="test-session",
        created_at="2026-07-05T00:00:00Z",
        image_filename=None,
        extraction=VisionExtractionResult(),
        diagnoses=[],
        report="test report",
        metadata={"source": "test"},
    )
    save_response = client.post("/history", json=session.model_dump())
    assert save_response.status_code == 200
    assert save_response.json()["id"] == "test-session"

    list_response = client.get("/history")
    assert list_response.status_code == 200
    assert any(item["id"] == "test-session" for item in list_response.json())

    detail_response = client.get("/history/test-session")
    assert detail_response.status_code == 200
    assert detail_response.json()["report"] == "test report"
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest tests/test_api.py -v
```

Expected: FAIL because `/rules` and `/history` endpoints are not implemented.

- [ ] **Step 3: Add seed rule data**

Create `backend/data/build_rules.json`:

```json
[
  {
    "character_name": "default_main_dps",
    "role": "main_dps",
    "recommended_sets": ["Molten Rift", "Void Thunder", "Freezing Frost", "Sierra Gale", "Celestial Light", "Havoc Eclipse"],
    "priority_stats": ["Crit Rate", "Crit DMG", "ATK%", "Element DMG Bonus", "Energy Regen"],
    "useful_sub_stats": ["Crit Rate", "Crit DMG", "ATK%", "ATK", "Energy Regen", "Resonance Skill DMG Bonus", "Resonance Liberation DMG Bonus"],
    "bad_sub_stats": ["DEF", "DEF%", "HP", "HP%"],
    "recommended_weapons": [],
    "notes": "Default DPS rule. Replace with character-specific rules later.",
    "source_links": [],
    "game_version": "manual"
  },
  {
    "character_name": "default_support",
    "role": "support",
    "recommended_sets": ["Moonlit Clouds", "Rejuvenation Glow"],
    "priority_stats": ["Energy Regen", "ATK%", "HP%", "Healing Bonus"],
    "useful_sub_stats": ["Energy Regen", "ATK%", "HP%", "Crit Rate", "Crit DMG"],
    "bad_sub_stats": ["DEF", "DEF%"],
    "recommended_weapons": [],
    "notes": "Default support rule.",
    "source_links": [],
    "game_version": "manual"
  }
]
```

Create `backend/data/team_rules.json`:

```json
[
  {
    "name": "Starter balanced team",
    "core_character": "default_main_dps",
    "recommended_teammates": ["default_sub_dps", "default_support"],
    "notes": "Placeholder team rule for MVP account planning."
  }
]
```

- [ ] **Step 4: Implement persistence services**

Create `backend/src/database.py`:

```python
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "wuwa_ai_coach.db"


def database_path() -> Path:
    url = os.getenv("DATABASE_URL")
    if url and url.startswith("sqlite:///"):
        return Path(url.removeprefix("sqlite:///")).resolve()
    return DEFAULT_DB_PATH


def get_connection() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                image_filename TEXT,
                extraction_json TEXT NOT NULL,
                diagnoses_json TEXT NOT NULL,
                report TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rules (
                id TEXT PRIMARY KEY,
                character_name TEXT NOT NULL,
                role TEXT NOT NULL,
                rule_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
```

Create `backend/src/rules.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from .models import BuildRule, TeamRule

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BUILD_RULES_PATH = DATA_DIR / "build_rules.json"
TEAM_RULES_PATH = DATA_DIR / "team_rules.json"


def load_build_rules(path: Path | None = None) -> list[BuildRule]:
    rule_path = path or BUILD_RULES_PATH
    with rule_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return [BuildRule.model_validate(item) for item in data]


def save_build_rules(rules: list[BuildRule], path: Path | None = None) -> list[BuildRule]:
    rule_path = path or BUILD_RULES_PATH
    rule_path.parent.mkdir(parents=True, exist_ok=True)
    validated = [BuildRule.model_validate(rule) for rule in rules]
    with rule_path.open("w", encoding="utf-8") as file:
        json.dump([rule.model_dump() for rule in validated], file, ensure_ascii=False, indent=2)
    return validated


def load_team_rules(path: Path | None = None) -> list[TeamRule]:
    rule_path = path or TEAM_RULES_PATH
    with rule_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return [TeamRule.model_validate(item) for item in data]
```

Create `backend/src/history.py`:

```python
from __future__ import annotations

import json

from .database import get_connection
from .models import AnalysisSession, Diagnosis, VisionExtractionResult


def save_session(session: AnalysisSession) -> AnalysisSession:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO analysis_sessions
            (id, created_at, image_filename, extraction_json, diagnoses_json, report, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.id,
                session.created_at,
                session.image_filename,
                session.extraction.model_dump_json(),
                json.dumps([diagnosis.model_dump() for diagnosis in session.diagnoses], ensure_ascii=False),
                session.report,
                json.dumps(session.metadata, ensure_ascii=False),
            ),
        )
        conn.commit()
    return session


def _row_to_session(row) -> AnalysisSession:
    return AnalysisSession(
        id=row["id"],
        created_at=row["created_at"],
        image_filename=row["image_filename"],
        extraction=VisionExtractionResult.model_validate_json(row["extraction_json"]),
        diagnoses=[Diagnosis.model_validate(item) for item in json.loads(row["diagnoses_json"])],
        report=row["report"],
        metadata=json.loads(row["metadata_json"]),
    )


def list_sessions(limit: int = 20) -> list[AnalysisSession]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM analysis_sessions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_session(row) for row in rows]


def get_session(session_id: str) -> AnalysisSession | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM analysis_sessions WHERE id = ?", (session_id,)).fetchone()
    return _row_to_session(row) if row else None
```

Create `backend/src/export_import.py`:

```python
from __future__ import annotations

from typing import Any

from .history import list_sessions, save_session
from .models import AnalysisSession, BuildRule
from .rules import load_build_rules, save_build_rules


def export_all() -> dict[str, Any]:
    return {
        "rules": [rule.model_dump() for rule in load_build_rules()],
        "history": [session.model_dump() for session in list_sessions(limit=200)],
    }


def import_all(payload: dict[str, Any]) -> dict[str, int]:
    rules = [BuildRule.model_validate(item) for item in payload.get("rules", [])]
    sessions = [AnalysisSession.model_validate(item) for item in payload.get("history", [])]
    if rules:
        save_build_rules(rules)
    for session in sessions:
        save_session(session)
    return {"rules": len(rules), "history": len(sessions)}
```

- [ ] **Step 5: Add API routes**

Modify `backend/main.py` to initialize the DB and expose routes:

```python
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.database import init_db
from src.export_import import export_all, import_all
from src.history import get_session, list_sessions, save_session
from src.models import AnalysisSession, BuildRule
from src.rules import load_build_rules, save_build_rules

app = FastAPI(title="WuWa AI Coach API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/rules", response_model=list[BuildRule])
def get_rules() -> list[BuildRule]:
    return load_build_rules()


@app.post("/rules", response_model=list[BuildRule])
def post_rules(rules: list[BuildRule]) -> list[BuildRule]:
    return save_build_rules(rules)


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
```

- [ ] **Step 6: Run tests**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest tests/test_api.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach
git add backend
git commit -m "feat: add rules history and export services"
```

---

### Task 3: Vision Extraction, JSON Parser, and Mock Mode

**Files:**
- Create: `backend/src/parser.py`
- Create: `backend/src/vision.py`
- Create: `backend/data/sample_extraction.json`
- Modify: `backend/main.py`
- Modify: `backend/tests/test_api.py`

**Interfaces:**
- Produces: `extract_json_object(text: str) -> dict[str, Any]`
- Produces: `normalize_extraction(data: dict[str, Any], raw_output: str | None = None) -> VisionExtractionResult`
- Produces: `extract_from_image(image_bytes: bytes, filename: str | None = None) -> VisionExtractionResult`
- Produces: `POST /vision/extract`

- [ ] **Step 1: Add failing mock extraction API test**

Append to `backend/tests/test_api.py`:

```python
def test_vision_extract_uses_mock_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post(
        "/vision/extract",
        files={"file": ("sample.png", b"not-a-real-image", "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["screen_type"] in ["character_status", "echo_detail", "weapon_detail", "inventory", "team", "unknown"]
    assert len(data["snapshot"]["echoes"]) == 5
    assert any("mock" in warning.lower() for warning in data["warnings"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest tests/test_api.py::test_vision_extract_uses_mock_without_api_key -v
```

Expected: FAIL because `/vision/extract` is not implemented.

- [ ] **Step 3: Add sample extraction data**

Create `backend/data/sample_extraction.json`:

```json
{
  "screen_type": "character_status",
  "snapshot": {
    "character_name": "Sample Rover",
    "character_level": 80,
    "role": "main_dps",
    "weapon": {
      "name": "Sample Broadblade",
      "level": 80,
      "rank": 1,
      "main_stat": "ATK%"
    },
    "stats": {
      "hp": "15200",
      "atk": "1850",
      "defense": "1200",
      "crit_rate": "62%",
      "crit_dmg": "210%",
      "energy_regen": "122%",
      "element_dmg_bonus": "30%",
      "healing_bonus": null
    },
    "echoes": [
      {
        "name": "Sample Echo 1",
        "slot": "1",
        "set_name": "Molten Rift",
        "cost": 4,
        "level": 25,
        "main_stat": "Crit Rate",
        "sub_stats": [
          {"name": "Crit DMG", "value": "16.2%"},
          {"name": "ATK%", "value": "9.4%"}
        ]
      }
    ],
    "raw_text": "Sample mock extraction used because no OpenAI API key is configured."
  },
  "uncertain_fields": [],
  "warnings": ["Mock extraction mode: OPENAI_API_KEY is not configured."],
  "confidence": 0.5,
  "raw_model_output": null
}
```

- [ ] **Step 4: Implement parser and vision modules**

Create `backend/src/parser.py`:

```python
from __future__ import annotations

import json
from typing import Any

from .models import EchoItem, VisionExtractionResult


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(stripped[start : end + 1])


def normalize_extraction(data: dict[str, Any], raw_output: str | None = None) -> VisionExtractionResult:
    result = VisionExtractionResult.model_validate(data)
    echoes = list(result.snapshot.echoes)
    while len(echoes) < 5:
        echoes.append(EchoItem(slot=str(len(echoes) + 1)))
    result.snapshot.echoes = echoes[:5]
    if raw_output is not None:
        result.raw_model_output = raw_output
    return result
```

Create `backend/src/vision.py`:

```python
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from openai import OpenAI

from .models import VisionExtractionResult
from .parser import extract_json_object, normalize_extraction

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SAMPLE_EXTRACTION_PATH = DATA_DIR / "sample_extraction.json"

VISION_PROMPT = """You are analyzing screenshots from Wuthering Waves.
Extract only visible information.
Do not guess missing fields.
Return strict JSON matching the schema.
If a value is unclear, set it to null and add the field path to uncertain_fields.
Preserve raw visible text in raw_text."""


def _load_mock_result() -> VisionExtractionResult:
    with SAMPLE_EXTRACTION_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    result = normalize_extraction(data)
    if not any("mock" in warning.lower() for warning in result.warnings):
        result.warnings.append("Mock extraction mode: OPENAI_API_KEY is not configured.")
    return result


def extract_from_image(image_bytes: bytes, filename: str | None = None) -> VisionExtractionResult:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _load_mock_result()

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=api_key)
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": VISION_PROMPT},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{image_b64}"},
                    ],
                }
            ],
        )
        raw_output = response.output_text
        data = extract_json_object(raw_output)
        return normalize_extraction(data, raw_output=raw_output)
    except Exception as exc:
        return VisionExtractionResult(
            warnings=[f"Vision extraction failed: {exc}"],
            raw_model_output=str(exc),
        )
```

- [ ] **Step 5: Add vision endpoint**

Modify `backend/main.py` imports and route:

```python
from fastapi import FastAPI, File, HTTPException, UploadFile
from src.models import AnalysisSession, BuildRule, VisionExtractionResult
from src.vision import extract_from_image


@app.post("/vision/extract", response_model=VisionExtractionResult)
async def post_vision_extract(file: UploadFile = File(...)) -> VisionExtractionResult:
    image_bytes = await file.read()
    return extract_from_image(image_bytes, file.filename)
```

- [ ] **Step 6: Run tests**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest tests/test_api.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach
git add backend
git commit -m "feat: add vision extraction mock mode"
```

---

### Task 4: Evaluator, Report, and Analysis Endpoints

**Files:**
- Create: `backend/src/evaluator.py`
- Create: `backend/src/report.py`
- Create: `backend/tests/test_evaluator.py`
- Modify: `backend/main.py`
- Modify: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: `CharacterSnapshot`, `EchoItem`, `BuildRule`
- Produces: `choose_rule(character_name: str | None, rules: list[BuildRule], fallback_role: Role) -> BuildRule`
- Produces: `evaluate_echo(echo: EchoItem, rule: BuildRule) -> Diagnosis`
- Produces: `evaluate_character(snapshot: CharacterSnapshot, rule: BuildRule) -> list[Diagnosis]`
- Produces: `evaluate_account(profile: dict[str, Any]) -> list[Diagnosis]`
- Produces: `generate_report(snapshot: CharacterSnapshot, diagnoses: list[Diagnosis]) -> str`
- Produces: `POST /analyze/echo`, `POST /analyze/character`, `POST /analyze/account`, `POST /report`

- [ ] **Step 1: Add evaluator tests**

Create `backend/tests/test_evaluator.py`:

```python
from src.evaluator import evaluate_echo, grade_for_score
from src.models import BuildRule, EchoItem, SubStat


def test_grade_thresholds():
    assert grade_for_score(85) == "excellent"
    assert grade_for_score(70) == "keep"
    assert grade_for_score(50) == "upgrade"
    assert grade_for_score(30) == "hold"
    assert grade_for_score(10) == "replace"
    assert grade_for_score(0) == "discard"


def test_evaluate_echo_scores_matching_stats():
    rule = BuildRule(
        character_name="default_main_dps",
        role="main_dps",
        recommended_sets=["Molten Rift"],
        priority_stats=["Crit Rate", "Crit DMG", "ATK%"],
        useful_sub_stats=["Crit Rate", "Crit DMG", "ATK%"],
        bad_sub_stats=["DEF"],
    )
    echo = EchoItem(
        name="Good Echo",
        set_name="Molten Rift",
        level=25,
        main_stat="Crit Rate",
        sub_stats=[SubStat(name="Crit DMG", value="16%"), SubStat(name="ATK%", value="8%")],
    )
    diagnosis = evaluate_echo(echo, rule)
    assert diagnosis.target_type == "echo"
    assert diagnosis.score >= 75
    assert diagnosis.grade in ["keep", "excellent"]
```

- [ ] **Step 2: Add analysis API test**

Append to `backend/tests/test_api.py`:

```python
def test_analyze_character_returns_diagnoses_and_report():
    extraction = client.post(
        "/vision/extract",
        files={"file": ("sample.png", b"sample", "image/png")},
    ).json()
    response = client.post(
        "/analyze/character",
        json={"snapshot": extraction["snapshot"], "fallback_role": "main_dps"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["diagnoses"]
    assert "바로 할 일" in data["report"] or "Next actions" in data["report"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest tests/test_evaluator.py tests/test_api.py::test_analyze_character_returns_diagnoses_and_report -v
```

Expected: FAIL because evaluator and analysis routes are not implemented.

- [ ] **Step 4: Implement evaluator**

Create `backend/src/evaluator.py`:

```python
from __future__ import annotations

from typing import Any

from .models import BuildRule, CharacterSnapshot, Diagnosis, EchoItem, Grade, Role


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def grade_for_score(score: int) -> Grade:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "keep"
    if score >= 50:
        return "upgrade"
    if score >= 30:
        return "hold"
    if score >= 10:
        return "replace"
    return "discard"


def choose_rule(character_name: str | None, rules: list[BuildRule], fallback_role: Role) -> BuildRule:
    wanted_name = _norm(character_name)
    for rule in rules:
        if wanted_name and _norm(rule.character_name) == wanted_name:
            return rule
    fallback_name = f"default_{fallback_role}"
    for rule in rules:
        if _norm(rule.character_name) == fallback_name:
            return rule
    for rule in rules:
        if rule.role == fallback_role:
            return rule
    return rules[0]


def evaluate_echo(echo: EchoItem, rule: BuildRule) -> Diagnosis:
    score = 0
    reasons: list[str] = []
    actions: list[str] = []
    recommended_sets = {_norm(item) for item in rule.recommended_sets}
    priority_stats = {_norm(item) for item in rule.priority_stats}
    useful_sub_stats = {_norm(item) for item in rule.useful_sub_stats}
    bad_sub_stats = {_norm(item) for item in rule.bad_sub_stats}

    if _norm(echo.set_name) in recommended_sets:
        score += 20
        reasons.append("Echo set matches a recommended set.")
    else:
        actions.append("Replace this echo with one from a recommended set.")

    if _norm(echo.main_stat) in priority_stats:
        score += 25
        reasons.append("Main stat matches the build priority.")
    else:
        actions.append("Farm an echo with a priority main stat.")

    sub_stat_names = {_norm(stat.name) for stat in echo.sub_stats if stat.name}
    useful_hits = len(sub_stat_names & useful_sub_stats)
    bad_hits = len(sub_stat_names & bad_sub_stats)
    score += useful_hits * 15
    score -= bad_hits * 15
    if useful_hits:
        reasons.append(f"{useful_hits} useful sub-stat(s) found.")
    if bad_hits:
        reasons.append(f"{bad_hits} low-value sub-stat(s) found.")
        actions.append("Avoid investing more unless this slot is temporary.")
    if {"crit rate", "crit dmg"}.issubset(sub_stat_names):
        score += 10
        reasons.append("Crit Rate and Crit DMG are both present.")

    score = max(0, min(100, score))
    if echo.level is not None and echo.level < 25 and score >= 60:
        actions.append("This echo is worth leveling further.")
    if not actions:
        actions.append("Keep this echo unless a stronger replacement appears.")

    return Diagnosis(
        target_type="echo",
        target_name=echo.name or echo.slot,
        grade=grade_for_score(score),
        score=score,
        reasons=reasons or ["Not enough echo data to score confidently."],
        recommended_actions=actions,
    )


def evaluate_character(snapshot: CharacterSnapshot, rule: BuildRule) -> list[Diagnosis]:
    echo_diagnoses = [evaluate_echo(echo, rule) for echo in snapshot.echoes]
    echo_scores = [diagnosis.score for diagnosis in echo_diagnoses]
    average = round(sum(echo_scores) / len(echo_scores)) if echo_scores else 0
    reasons = [f"Average echo score is {average}."]
    actions = ["Fix the lowest-scoring echo first.", "Prioritize main stats before chasing perfect sub-stats."]
    if snapshot.weapon and snapshot.weapon.name in rule.recommended_weapons:
        average = min(100, average + 10)
        reasons.append("Weapon is listed as recommended.")
    elif rule.recommended_weapons:
        actions.append("Compare the current weapon against recommended options.")
    character_diagnosis = Diagnosis(
        target_type="character",
        target_name=snapshot.character_name,
        grade=grade_for_score(average),
        score=average,
        reasons=reasons,
        recommended_actions=actions,
    )
    return echo_diagnoses + [character_diagnosis]


def evaluate_account(profile: dict[str, Any]) -> list[Diagnosis]:
    owned = profile.get("characters", [])
    score = 50 if owned else 20
    return [
        Diagnosis(
            target_type="account",
            target_name="Account plan",
            grade=grade_for_score(score),
            score=score,
            reasons=["MVP account evaluation uses submitted character list only."],
            recommended_actions=[
                "Build one main DPS first.",
                "Add one support and one sub DPS before optimizing luxury upgrades.",
            ],
        )
    ]
```

- [ ] **Step 5: Implement report generator**

Create `backend/src/report.py`:

```python
from __future__ import annotations

from .models import CharacterSnapshot, Diagnosis


def generate_report(snapshot: CharacterSnapshot, diagnoses: list[Diagnosis]) -> str:
    sorted_items = sorted(diagnoses, key=lambda item: item.score)
    biggest_problems = sorted_items[:3]
    actions: list[str] = []
    for diagnosis in biggest_problems:
        actions.extend(diagnosis.recommended_actions[:1])
    actions = actions[:3] or ["Enter more character and echo data, then run diagnosis again."]
    character = snapshot.character_name or "Current character"
    lines = [
        "요약",
        f"{character}의 현재 빌드는 에코와 핵심 스탯을 우선 점검해야 합니다.",
        "",
        "현재 상태",
        f"진단 항목 {len(diagnoses)}개를 평가했습니다.",
        "",
        "가장 큰 문제 3개",
    ]
    lines.extend(f"- {item.target_name or item.target_type}: {item.grade} ({item.score})" for item in biggest_problems)
    lines.extend(["", "바로 할 일 3개"])
    lines.extend(f"- {action}" for action in actions)
    lines.extend(["", "보류해도 되는 것", "- 완벽한 부옵션 파밍은 기본 세트와 주옵션을 맞춘 뒤 진행하세요."])
    lines.extend(["", "장기 목표", "- 역할에 맞는 무기, 세트, 치명/공격/에너지 균형을 안정화하세요."])
    lines.extend(["", "주의사항", "- 이 결과는 비공식 팬 도구의 추정이며 게임 내 실제 성능과 다를 수 있습니다."])
    return "\n".join(lines)
```

- [ ] **Step 6: Add analysis routes**

Modify `backend/main.py`:

```python
from typing import Any

from src.evaluator import choose_rule, evaluate_account, evaluate_character, evaluate_echo
from src.models import AnalysisSession, AnalyzeRequest, AnalyzeResponse, BuildRule, Diagnosis, EchoItem, VisionExtractionResult
from src.report import generate_report


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
```

- [ ] **Step 7: Run tests**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run pytest -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach
git add backend
git commit -m "feat: add diagnosis and report generation"
```

---

### Task 5: Optional Adapter Placeholders and Backend Compile Verification

**Files:**
- Create: `backend/src/optional_ocr.py`
- Create: `backend/src/optional_local_vision.py`
- Modify: `README.md`

**Interfaces:**
- Produces: `extract_text_with_optional_ocr(image_bytes: bytes) -> None`
- Produces: `analyze_with_local_vision(image_bytes: bytes) -> None`

- [ ] **Step 1: Add placeholder interfaces**

Create `backend/src/optional_ocr.py`:

```python
from __future__ import annotations


def extract_text_with_optional_ocr(image_bytes: bytes) -> None:
    """Placeholder for a future OCR fallback; intentionally unused in the MVP path."""
    return None
```

Create `backend/src/optional_local_vision.py`:

```python
from __future__ import annotations


def analyze_with_local_vision(image_bytes: bytes) -> None:
    """Placeholder for future SAM3/DINOv3/local vision adapters."""
    return None
```

- [ ] **Step 2: Run backend verification**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run python -m compileall .
uv run pytest -v
```

Expected: compileall finishes without syntax errors and pytest passes.

- [ ] **Step 3: Commit**

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach
git add backend
git commit -m "feat: add optional vision extension placeholders"
```

---

### Task 6: Frontend Tooling, Types, API Client, and Shell

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/eslint.config.mjs`
- Create: `frontend/src/app/globals.css`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/constants.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/components/AppShell.tsx`

**Interfaces:**
- Produces: `ApiError extends Error`
- Produces: `extractVision(file: File)`, `analyzeCharacter(snapshot, fallbackRole)`, `getRules()`, `saveRules(rules)`, `getHistory()`, `saveHistory(session)`, `exportData()`, `importData(payload)`
- Produces: `AppShell` component with tab state and content slots

- [ ] **Step 1: Create package and config files**

Create `frontend/package.json`:

```json
{
  "name": "wuwa-ai-coach-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "15.3.4",
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "lucide-react": "^0.468.0"
  },
  "devDependencies": {
    "@eslint/eslintrc": "^3.3.0",
    "@types/node": "^22.10.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "autoprefixer": "^10.4.20",
    "eslint": "^9.18.0",
    "eslint-config-next": "15.3.4",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.7.0"
  }
}
```

Create `frontend/next.config.ts`:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {};

export default nextConfig;
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

Create `frontend/postcss.config.mjs`:

```javascript
const config = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};

export default config;
```

Create `frontend/eslint.config.mjs`:

```javascript
import { FlatCompat } from "@eslint/eslintrc";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({ baseDirectory: __dirname });

const eslintConfig = [...compat.extends("next/core-web-vitals", "next/typescript")];

export default eslintConfig;
```

- [ ] **Step 2: Create shared frontend types and constants**

Create `frontend/src/lib/types.ts` with TypeScript equivalents of backend models:

```typescript
export type Role = "main_dps" | "sub_dps" | "support" | "healer";
export type Grade = "excellent" | "keep" | "upgrade" | "hold" | "replace" | "discard";
export type ScreenType = "character_status" | "echo_detail" | "weapon_detail" | "inventory" | "team" | "unknown";

export interface StatBlock {
  hp?: string | null;
  atk?: string | null;
  defense?: string | null;
  crit_rate?: string | null;
  crit_dmg?: string | null;
  energy_regen?: string | null;
  element_dmg_bonus?: string | null;
  healing_bonus?: string | null;
}

export interface SubStat {
  name?: string | null;
  value?: string | null;
}

export interface EchoItem {
  name?: string | null;
  slot?: string | null;
  set_name?: string | null;
  cost?: number | null;
  level?: number | null;
  main_stat?: string | null;
  sub_stats: SubStat[];
}

export interface WeaponState {
  name?: string | null;
  level?: number | null;
  rank?: number | null;
  main_stat?: string | null;
}

export interface CharacterSnapshot {
  character_name?: string | null;
  character_level?: number | null;
  role?: Role | null;
  weapon?: WeaponState | null;
  stats: StatBlock;
  echoes: EchoItem[];
  raw_text: string;
}

export interface VisionExtractionResult {
  screen_type: ScreenType;
  snapshot: CharacterSnapshot;
  uncertain_fields: string[];
  warnings: string[];
  confidence?: number | null;
  raw_model_output?: string | null;
}

export interface BuildRule {
  character_name: string;
  role: Role;
  recommended_sets: string[];
  priority_stats: string[];
  useful_sub_stats: string[];
  bad_sub_stats: string[];
  recommended_weapons: string[];
  notes?: string | null;
  source_links: string[];
  game_version?: string | null;
}

export interface Diagnosis {
  target_type: "echo" | "character" | "account" | "team";
  target_name?: string | null;
  grade: Grade;
  score: number;
  reasons: string[];
  recommended_actions: string[];
}

export interface AnalysisSession {
  id: string;
  created_at: string;
  image_filename?: string | null;
  extraction: VisionExtractionResult;
  diagnoses: Diagnosis[];
  report: string;
  metadata: Record<string, unknown>;
}

export interface AnalyzeResponse {
  snapshot: CharacterSnapshot;
  diagnoses: Diagnosis[];
  report: string;
}
```

Create `frontend/src/lib/constants.ts`:

```typescript
import type { CharacterSnapshot, EchoItem, Role } from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const ROLES: Role[] = ["main_dps", "sub_dps", "support", "healer"];

export const TABS = ["Dashboard", "Analyzer", "Planner", "Teams", "Rules", "History", "Settings"] as const;
export type AppTab = (typeof TABS)[number];

export function emptyEcho(slot: number): EchoItem {
  return {
    name: "",
    slot: String(slot),
    set_name: "",
    cost: null,
    level: null,
    main_stat: "",
    sub_stats: [
      { name: "", value: "" },
      { name: "", value: "" },
    ],
  };
}

export function emptySnapshot(): CharacterSnapshot {
  return {
    character_name: "",
    character_level: null,
    role: "main_dps",
    weapon: { name: "", level: null, rank: null, main_stat: "" },
    stats: {},
    echoes: [1, 2, 3, 4, 5].map(emptyEcho),
    raw_text: "",
  };
}
```

- [ ] **Step 3: Create API client**

Create `frontend/src/lib/api.ts`:

```typescript
import { API_BASE_URL } from "./constants";
import type { AnalysisSession, AnalyzeResponse, BuildRule, CharacterSnapshot, Role, VisionExtractionResult } from "./types";

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(text || `API request failed: ${path}`, response.status);
  }
  return response.json() as Promise<T>;
}

export function health(): Promise<{ ok: boolean }> {
  return request("/health");
}

export function extractVision(file: File): Promise<VisionExtractionResult> {
  const form = new FormData();
  form.append("file", file);
  return request("/vision/extract", { method: "POST", body: form });
}

export function analyzeCharacter(snapshot: CharacterSnapshot, fallbackRole: Role): Promise<AnalyzeResponse> {
  return request("/analyze/character", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snapshot, fallback_role: fallbackRole }),
  });
}

export function getRules(): Promise<BuildRule[]> {
  return request("/rules");
}

export function saveRules(rules: BuildRule[]): Promise<BuildRule[]> {
  return request("/rules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rules),
  });
}

export function getHistory(): Promise<AnalysisSession[]> {
  return request("/history");
}

export function saveHistory(session: AnalysisSession): Promise<AnalysisSession> {
  return request("/history", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(session),
  });
}

export function exportData(): Promise<Record<string, unknown>> {
  return request("/export");
}

export function importData(payload: Record<string, unknown>): Promise<{ rules: number; history: number }> {
  return request("/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
```

- [ ] **Step 4: Add root layout, CSS, and app shell**

Create `frontend/src/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color-scheme: light;
  background: #f4f7fb;
  color: #172033;
}

body {
  margin: 0;
  background: #f4f7fb;
}

button,
input,
select,
textarea {
  font: inherit;
}
```

Create `frontend/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WuWa AI Coach",
  description: "Unofficial Wuthering Waves account and echo coaching tool",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```

Create `frontend/src/components/AppShell.tsx`:

```tsx
"use client";

import { useState } from "react";
import { TABS, type AppTab } from "@/lib/constants";

interface AppShellProps {
  renderTab: (tab: AppTab) => React.ReactNode;
}

export function AppShell({ renderTab }: AppShellProps) {
  const [activeTab, setActiveTab] = useState<AppTab>("Analyzer");

  return (
    <main className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold tracking-normal text-slate-950">WuWa AI Coach</h1>
              <p className="text-sm text-slate-600">Wuthering Waves screenshot and build coaching</p>
            </div>
            <span className="rounded-md border border-amber-300 bg-amber-50 px-3 py-1 text-sm font-medium text-amber-900">
              비공식 팬 도구
            </span>
          </div>
          <nav className="flex gap-2 overflow-x-auto">
            {TABS.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`rounded-md px-3 py-2 text-sm font-medium ${
                  activeTab === tab ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <section className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{renderTab(activeTab)}</section>
    </main>
  );
}
```

Create `frontend/src/app/page.tsx`:

```tsx
"use client";

import { AppShell } from "@/components/AppShell";
import type { AppTab } from "@/lib/constants";

export default function Home() {
  return (
    <AppShell
      renderTab={(tab: AppTab) => (
        <div className="rounded-md border border-slate-200 bg-white p-6 text-slate-700">
          {tab} is being wired in this MVP.
        </div>
      )}
    />
  );
}
```

- [ ] **Step 5: Install frontend dependencies and run lint/build**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\frontend
npm install
npm run lint
npm run build
```

Expected: dependencies install, lint passes, build passes.

- [ ] **Step 6: Commit**

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach
git add frontend
git commit -m "feat: add frontend shell and API client"
```

---

### Task 7: Analyzer Flow Components

**Files:**
- Create: `frontend/src/components/ImageUploader.tsx`
- Create: `frontend/src/components/ExtractionPanel.tsx`
- Create: `frontend/src/components/EchoEditor.tsx`
- Create: `frontend/src/components/DiagnosisResult.tsx`
- Create: `frontend/src/components/ScreenshotAnalyzer.tsx`
- Modify: `frontend/src/app/page.tsx`

**Interfaces:**
- Consumes: `extractVision`, `analyzeCharacter`, `saveHistory`
- Produces: a working Analyzer tab that supports upload, mock extraction, manual editing, diagnosis, JSON download, and history save

- [ ] **Step 1: Create ImageUploader**

Create `frontend/src/components/ImageUploader.tsx`:

```tsx
interface ImageUploaderProps {
  previewUrl: string | null;
  onFileSelected: (file: File) => void;
}

export function ImageUploader({ previewUrl, onFileSelected }: ImageUploaderProps) {
  return (
    <section className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-4">
      <label className="block text-sm font-medium text-slate-700" htmlFor="screenshot-file">
        Screenshot
      </label>
      <input
        id="screenshot-file"
        type="file"
        accept="image/*"
        className="mt-2 block w-full text-sm text-slate-700"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFileSelected(file);
        }}
      />
      {previewUrl ? (
        <img src={previewUrl} alt="Uploaded screenshot preview" className="mt-4 max-h-80 w-full rounded-md object-contain" />
      ) : (
        <div className="mt-4 flex h-48 items-center justify-center rounded-md border border-slate-200 bg-white text-sm text-slate-500">
          Image preview appears here
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Create ExtractionPanel**

Create `frontend/src/components/ExtractionPanel.tsx`:

```tsx
import type { VisionExtractionResult } from "@/lib/types";

interface ExtractionPanelProps {
  extraction: VisionExtractionResult | null;
}

export function ExtractionPanel({ extraction }: ExtractionPanelProps) {
  if (!extraction) {
    return <section className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-500">No extraction yet.</section>;
  }
  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-950">Extraction</h2>
        <span className="text-sm text-slate-500">Screen: {extraction.screen_type}</span>
      </div>
      {extraction.warnings.length > 0 && (
        <ul className="mb-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          {extraction.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
      <details className="mb-3">
        <summary className="cursor-pointer text-sm font-medium text-slate-700">Raw text</summary>
        <pre className="mt-2 whitespace-pre-wrap rounded-md bg-slate-100 p-3 text-xs text-slate-700">{extraction.snapshot.raw_text}</pre>
      </details>
      <details>
        <summary className="cursor-pointer text-sm font-medium text-slate-700">JSON</summary>
        <pre className="mt-2 max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-50">
          {JSON.stringify(extraction, null, 2)}
        </pre>
      </details>
    </section>
  );
}
```

- [ ] **Step 3: Create EchoEditor**

Create `frontend/src/components/EchoEditor.tsx`:

```tsx
import { emptyEcho } from "@/lib/constants";
import type { EchoItem } from "@/lib/types";

interface EchoEditorProps {
  echoes: EchoItem[];
  onChange: (echoes: EchoItem[]) => void;
}

export function EchoEditor({ echoes, onChange }: EchoEditorProps) {
  const normalized = [...echoes];
  while (normalized.length < 5) normalized.push(emptyEcho(normalized.length + 1));

  function updateEcho(index: number, patch: Partial<EchoItem>) {
    const next = normalized.slice(0, 5).map((echo, echoIndex) => (echoIndex === index ? { ...echo, ...patch } : echo));
    onChange(next);
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-slate-950">Echoes</h2>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {normalized.slice(0, 5).map((echo, index) => (
          <div key={index} className="rounded-md border border-slate-200 p-3">
            <div className="grid gap-2 sm:grid-cols-2">
              <input className="rounded-md border px-3 py-2" placeholder="Echo name" value={echo.name ?? ""} onChange={(e) => updateEcho(index, { name: e.target.value })} />
              <input className="rounded-md border px-3 py-2" placeholder="Set" value={echo.set_name ?? ""} onChange={(e) => updateEcho(index, { set_name: e.target.value })} />
              <input className="rounded-md border px-3 py-2" placeholder="Main stat" value={echo.main_stat ?? ""} onChange={(e) => updateEcho(index, { main_stat: e.target.value })} />
              <input className="rounded-md border px-3 py-2" placeholder="Level" type="number" value={echo.level ?? ""} onChange={(e) => updateEcho(index, { level: e.target.value ? Number(e.target.value) : null })} />
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {(echo.sub_stats.length ? echo.sub_stats : [{ name: "", value: "" }]).slice(0, 5).map((stat, statIndex) => (
                <div key={statIndex} className="grid grid-cols-2 gap-2">
                  <input
                    className="rounded-md border px-2 py-1 text-sm"
                    placeholder="Sub stat"
                    value={stat.name ?? ""}
                    onChange={(event) => {
                      const sub_stats = [...echo.sub_stats];
                      sub_stats[statIndex] = { ...sub_stats[statIndex], name: event.target.value };
                      updateEcho(index, { sub_stats });
                    }}
                  />
                  <input
                    className="rounded-md border px-2 py-1 text-sm"
                    placeholder="Value"
                    value={stat.value ?? ""}
                    onChange={(event) => {
                      const sub_stats = [...echo.sub_stats];
                      sub_stats[statIndex] = { ...sub_stats[statIndex], value: event.target.value };
                      updateEcho(index, { sub_stats });
                    }}
                  />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Create DiagnosisResult**

Create `frontend/src/components/DiagnosisResult.tsx`:

```tsx
import type { AnalyzeResponse } from "@/lib/types";

interface DiagnosisResultProps {
  result: AnalyzeResponse | null;
}

export function DiagnosisResult({ result }: DiagnosisResultProps) {
  if (!result) {
    return <section className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-500">Run diagnosis to see results.</section>;
  }
  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-slate-950">Diagnosis Result</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {result.diagnoses.map((diagnosis, index) => (
          <article key={`${diagnosis.target_type}-${diagnosis.target_name}-${index}`} className="rounded-md border border-slate-200 p-3">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-medium text-slate-900">{diagnosis.target_name || diagnosis.target_type}</h3>
              <span className="rounded-md bg-slate-100 px-2 py-1 text-sm text-slate-700">{diagnosis.grade} · {diagnosis.score}</span>
            </div>
            <ul className="mt-3 list-disc pl-5 text-sm text-slate-600">
              {diagnosis.reasons.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
            <ul className="mt-3 list-disc pl-5 text-sm text-slate-800">
              {diagnosis.recommended_actions.map((action) => <li key={action}>{action}</li>)}
            </ul>
          </article>
        ))}
      </div>
      <pre className="mt-4 whitespace-pre-wrap rounded-md bg-slate-100 p-4 text-sm text-slate-800">{result.report}</pre>
    </section>
  );
}
```

- [ ] **Step 5: Create ScreenshotAnalyzer and wire page**

Create `frontend/src/components/ScreenshotAnalyzer.tsx`:

```tsx
"use client";

import { useMemo, useState } from "react";
import { analyzeCharacter, extractVision, saveHistory } from "@/lib/api";
import { emptySnapshot, ROLES } from "@/lib/constants";
import type { AnalyzeResponse, CharacterSnapshot, VisionExtractionResult } from "@/lib/types";
import { DiagnosisResult } from "./DiagnosisResult";
import { EchoEditor } from "./EchoEditor";
import { ExtractionPanel } from "./ExtractionPanel";
import { ImageUploader } from "./ImageUploader";

export function ScreenshotAnalyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [extraction, setExtraction] = useState<VisionExtractionResult | null>(null);
  const [snapshot, setSnapshot] = useState<CharacterSnapshot>(emptySnapshot());
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");

  const canDownload = useMemo(() => extraction || result, [extraction, result]);

  function updateSnapshot(patch: Partial<CharacterSnapshot>) {
    setSnapshot((current) => ({ ...current, ...patch }));
  }

  async function runExtraction() {
    if (!file) {
      setError("Select an image first.");
      return;
    }
    setError("");
    setStatus("Extracting screenshot...");
    try {
      const next = await extractVision(file);
      setExtraction(next);
      setSnapshot(next.snapshot);
      setStatus("Extraction ready.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extraction failed.");
    }
  }

  async function runDiagnosis() {
    setError("");
    setStatus("Running diagnosis...");
    try {
      const next = await analyzeCharacter(snapshot, snapshot.role ?? "main_dps");
      setResult(next);
      setStatus("Diagnosis complete.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Diagnosis failed.");
    }
  }

  async function saveCurrentHistory() {
    if (!extraction || !result) {
      setError("Run extraction and diagnosis before saving history.");
      return;
    }
    await saveHistory({
      id: crypto.randomUUID(),
      created_at: new Date().toISOString(),
      image_filename: file?.name ?? null,
      extraction,
      diagnoses: result.diagnoses,
      report: result.report,
      metadata: { source: "frontend" },
    });
    setStatus("Saved to history.");
  }

  function downloadJson() {
    const blob = new Blob([JSON.stringify({ extraction, result }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "wuwa-analysis.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="grid gap-4">
      <ImageUploader
        previewUrl={previewUrl}
        onFileSelected={(nextFile) => {
          setFile(nextFile);
          setPreviewUrl(URL.createObjectURL(nextFile));
        }}
      />
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={runExtraction} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white">Analyze Image</button>
        <button type="button" onClick={runDiagnosis} className="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white">Run Diagnosis</button>
        <button type="button" onClick={saveCurrentHistory} className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700">Save History</button>
        <button type="button" disabled={!canDownload} onClick={downloadJson} className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-50">Download JSON</button>
      </div>
      {status && <p className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">{status}</p>}
      {error && <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p>}
      <section className="rounded-md border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-950">Manual Editor</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          <input className="rounded-md border px-3 py-2" placeholder="Character" value={snapshot.character_name ?? ""} onChange={(e) => updateSnapshot({ character_name: e.target.value })} />
          <input className="rounded-md border px-3 py-2" placeholder="Level" type="number" value={snapshot.character_level ?? ""} onChange={(e) => updateSnapshot({ character_level: e.target.value ? Number(e.target.value) : null })} />
          <select className="rounded-md border px-3 py-2" value={snapshot.role ?? "main_dps"} onChange={(e) => updateSnapshot({ role: e.target.value as CharacterSnapshot["role"] })}>
            {ROLES.map((role) => <option key={role} value={role}>{role}</option>)}
          </select>
          <input className="rounded-md border px-3 py-2" placeholder="Weapon" value={snapshot.weapon?.name ?? ""} onChange={(e) => updateSnapshot({ weapon: { ...(snapshot.weapon ?? {}), name: e.target.value } })} />
        </div>
      </section>
      <EchoEditor echoes={snapshot.echoes} onChange={(echoes) => updateSnapshot({ echoes })} />
      <ExtractionPanel extraction={extraction} />
      <DiagnosisResult result={result} />
    </div>
  );
}
```

Modify `frontend/src/app/page.tsx` to render Analyzer:

```tsx
"use client";

import { AppShell } from "@/components/AppShell";
import { ScreenshotAnalyzer } from "@/components/ScreenshotAnalyzer";
import type { AppTab } from "@/lib/constants";

export default function Home() {
  return (
    <AppShell
      renderTab={(tab: AppTab) => {
        if (tab === "Analyzer") return <ScreenshotAnalyzer />;
        return <div className="rounded-md border border-slate-200 bg-white p-6 text-slate-700">{tab} is being wired in this MVP.</div>;
      }}
    />
  );
}
```

- [ ] **Step 6: Run lint/build**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\frontend
npm run lint
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach
git add frontend
git commit -m "feat: add screenshot analyzer flow"
```

---

### Task 8: Dashboard, Rules, History, Settings, Planner, and Teams

**Files:**
- Create: `frontend/src/components/Dashboard.tsx`
- Create: `frontend/src/components/RulesManager.tsx`
- Create: `frontend/src/components/HistoryPanel.tsx`
- Create: `frontend/src/components/SettingsPanel.tsx`
- Create: `frontend/src/components/CharacterPlanner.tsx`
- Create: `frontend/src/components/TeamBuilder.tsx`
- Modify: `frontend/src/app/page.tsx`

**Interfaces:**
- Consumes: `getRules`, `saveRules`, `getHistory`, `exportData`, `importData`
- Produces: all required MVP tabs with working rules/history/settings and explicit MVP planner/team placeholders

- [ ] **Step 1: Create Dashboard, Planner, and Teams panels**

Create `frontend/src/components/Dashboard.tsx`:

```tsx
export function Dashboard() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {[
        ["Recent analysis", "Use History after saving a diagnosis."],
        ["Current priority", "Run Analyzer to identify the weakest echo first."],
        ["Next action", "Fix main stats before optimizing sub-stats."],
      ].map(([title, body]) => (
        <section key={title} className="rounded-md border border-slate-200 bg-white p-4">
          <h2 className="font-semibold text-slate-950">{title}</h2>
          <p className="mt-2 text-sm text-slate-600">{body}</p>
        </section>
      ))}
    </div>
  );
}
```

Create `frontend/src/components/CharacterPlanner.tsx`:

```tsx
export function CharacterPlanner() {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-slate-950">Character Planner</h2>
      <p className="mt-2 text-sm text-slate-600">MVP planning uses saved diagnoses. Build one main DPS first, then one support, then improve echo quality.</p>
    </section>
  );
}
```

Create `frontend/src/components/TeamBuilder.tsx`:

```tsx
export function TeamBuilder() {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-slate-950">Team Builder</h2>
      <p className="mt-2 text-sm text-slate-600">MVP team advice is role-based: main DPS, sub DPS, and support/healer. Owned-character recommendations come in a later phase.</p>
    </section>
  );
}
```

- [ ] **Step 2: Create RulesManager**

Create `frontend/src/components/RulesManager.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { getRules, saveRules } from "@/lib/api";

export function RulesManager() {
  const [text, setText] = useState("[]");
  const [message, setMessage] = useState("");

  useEffect(() => {
    getRules().then((rules) => setText(JSON.stringify(rules, null, 2))).catch((error) => setMessage(error.message));
  }, []);

  async function save() {
    try {
      const parsed = JSON.parse(text);
      const rules = await saveRules(parsed);
      setText(JSON.stringify(rules, null, 2));
      setMessage("Rules saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Rules save failed.");
    }
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-950">Rules Manager</h2>
        <button type="button" onClick={save} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white">Save Rules</button>
      </div>
      {message && <p className="mt-3 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">{message}</p>}
      <textarea className="mt-4 min-h-[28rem] w-full rounded-md border border-slate-300 p-3 font-mono text-sm" value={text} onChange={(event) => setText(event.target.value)} />
    </section>
  );
}
```

- [ ] **Step 3: Create HistoryPanel and SettingsPanel**

Create `frontend/src/components/HistoryPanel.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { getHistory } from "@/lib/api";
import type { AnalysisSession } from "@/lib/types";

export function HistoryPanel() {
  const [sessions, setSessions] = useState<AnalysisSession[]>([]);
  const [selected, setSelected] = useState<AnalysisSession | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getHistory().then(setSessions).catch((err) => setError(err.message));
  }, []);

  return (
    <section className="grid gap-4 lg:grid-cols-[20rem_1fr]">
      <div className="rounded-md border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-950">History</h2>
        {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
        <div className="mt-3 grid gap-2">
          {sessions.map((session) => (
            <button key={session.id} type="button" onClick={() => setSelected(session)} className="rounded-md border border-slate-200 p-3 text-left text-sm hover:bg-slate-50">
              <strong>{session.extraction.snapshot.character_name || "Unknown"}</strong>
              <span className="block text-slate-500">{new Date(session.created_at).toLocaleString()}</span>
            </button>
          ))}
        </div>
      </div>
      <pre className="min-h-96 overflow-auto rounded-md border border-slate-200 bg-white p-4 text-xs text-slate-700">
        {selected ? JSON.stringify(selected, null, 2) : "Select a saved session."}
      </pre>
    </section>
  );
}
```

Create `frontend/src/components/SettingsPanel.tsx`:

```tsx
"use client";

import { useState } from "react";
import { API_BASE_URL } from "@/lib/constants";
import { exportData, importData } from "@/lib/api";

export function SettingsPanel() {
  const [message, setMessage] = useState("");

  async function downloadExport() {
    const data = await exportData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "wuwa-ai-coach-export.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function uploadImport(file: File) {
    const payload = JSON.parse(await file.text());
    const result = await importData(payload);
    setMessage(`Imported ${result.rules} rules and ${result.history} history sessions.`);
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-slate-950">Settings</h2>
      <dl className="mt-4 grid gap-3 text-sm text-slate-700">
        <div><dt className="font-medium">API base URL</dt><dd>{API_BASE_URL}</dd></div>
        <div><dt className="font-medium">OpenAI API key</dt><dd>Set OPENAI_API_KEY in the backend environment to enable real vision extraction. Without it, mock mode is used.</dd></div>
        <div><dt className="font-medium">Legal notice</dt><dd>WuWa AI Coach is an unofficial fan tool and is not affiliated with Wuthering Waves or Kuro Games.</dd></div>
      </dl>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={downloadExport} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white">Export JSON</button>
        <label className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700">
          Import JSON
          <input type="file" accept="application/json" className="hidden" onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) uploadImport(file).catch((error) => setMessage(error.message));
          }} />
        </label>
      </div>
      {message && <p className="mt-3 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">{message}</p>}
    </section>
  );
}
```

- [ ] **Step 4: Wire all tabs**

Modify `frontend/src/app/page.tsx`:

```tsx
"use client";

import { Dashboard } from "@/components/Dashboard";
import { CharacterPlanner } from "@/components/CharacterPlanner";
import { HistoryPanel } from "@/components/HistoryPanel";
import { AppShell } from "@/components/AppShell";
import { RulesManager } from "@/components/RulesManager";
import { ScreenshotAnalyzer } from "@/components/ScreenshotAnalyzer";
import { SettingsPanel } from "@/components/SettingsPanel";
import { TeamBuilder } from "@/components/TeamBuilder";
import type { AppTab } from "@/lib/constants";

function renderTab(tab: AppTab) {
  switch (tab) {
    case "Dashboard":
      return <Dashboard />;
    case "Analyzer":
      return <ScreenshotAnalyzer />;
    case "Planner":
      return <CharacterPlanner />;
    case "Teams":
      return <TeamBuilder />;
    case "Rules":
      return <RulesManager />;
    case "History":
      return <HistoryPanel />;
    case "Settings":
      return <SettingsPanel />;
  }
}

export default function Home() {
  return <AppShell renderTab={renderTab} />;
}
```

- [ ] **Step 5: Run lint/build**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\frontend
npm run lint
npm run build
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach
git add frontend
git commit -m "feat: add MVP dashboard and management tabs"
```

---

### Task 9: README and End-to-End Verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Produces: documented setup and run workflow
- Produces: final verified MVP

- [ ] **Step 1: Write README**

Create `README.md`:

```markdown
# WuWa AI Coach

WuWa AI Coach is an unofficial Wuthering Waves fan tool for screenshot-based build and echo coaching. It is not affiliated with Wuthering Waves or Kuro Games.

## Features

- Screenshot upload and preview
- GPT Vision extraction when `OPENAI_API_KEY` is configured
- Mock extraction when no API key is configured
- Manual correction UI
- Five echo editor
- Rule-based echo and character diagnosis
- Local natural-language report
- SQLite history
- Rule JSON editing
- JSON export/import

## Backend Setup

```powershell
cd backend
uv init --bare --name wuwa-ai-coach-backend --no-pin-python --no-workspace
uv venv
uv add "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0" "pydantic>=2.8.0" "python-multipart>=0.0.9" "openai>=1.40.0"
uv add --dev "pytest>=8.2.0" "httpx>=0.27.0"
uv run uvicorn main:app --reload --port 8000
```

Optional environment variables:

```powershell
$env:OPENAI_API_KEY="..."
$env:OPENAI_MODEL="gpt-4.1-mini"
$env:DATABASE_URL="sqlite:///./wuwa_ai_coach.db"
```

If `OPENAI_API_KEY` is not set, `/vision/extract` returns `backend/data/sample_extraction.json` with a mock-mode warning.

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

Set a custom backend URL if needed:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
```

## Verification

Backend:

```powershell
cd backend
uv run python -m compileall .
uv run pytest -v
```

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

## Rules

Build rules live in `backend/data/build_rules.json`. Use the Rules tab to inspect and save edited rule JSON. MVP seed rules are intentionally small and role-oriented.

## Export and Import

Use Settings to export all local rules and history as JSON, or import a compatible JSON file.

## Legal and Operational Notes

- This is an unofficial fan tool.
- Do not upload screenshots containing sensitive information.
- Uploaded images are not stored by default.
- Official game assets are not bundled in this repository.
- External guide scraping is not implemented.
- OCR, SAM3, and DINOv3 are future extension points only.
```

- [ ] **Step 2: Run backend final verification**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run python -m compileall .
uv run pytest -v
```

Expected: PASS.

- [ ] **Step 3: Run frontend final verification**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\frontend
npm run lint
npm run build
```

Expected: PASS.

- [ ] **Step 4: Start backend and check health**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\backend
uv run uvicorn main:app --reload --port 8000
```

In another terminal:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected:

```text
ok
--
True
```

- [ ] **Step 5: Start frontend**

Run:

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach\frontend
npm run dev
```

Expected: Next.js starts on `http://localhost:3000`.

- [ ] **Step 6: Manual browser verification**

Verify:

- Analyzer opens as the default tab.
- Image upload shows a preview.
- Analyze Image returns mock extraction without an API key.
- Manual fields can be edited.
- Run Diagnosis returns diagnosis cards and a report.
- Save History stores the session.
- History shows the saved session.
- Rules loads and saves JSON.
- Settings export downloads JSON.
- Settings import accepts exported JSON.
- Header clearly shows `비공식 팬 도구`.
- Mobile-width layout does not overlap fields.

- [ ] **Step 7: Commit final docs**

```powershell
cd C:\Users\JungSu\Desktop\wawa-ai-coach
git add README.md
git commit -m "docs: add setup and usage guide"
```
