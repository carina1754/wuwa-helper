# WuWa AI Coach MVP Design

Date: 2026-07-05
Repository folder: `C:\Users\JungSu\Desktop\wawa-ai-coach`
Product name: `WuWa AI Coach`

## Goal

Build a full-stack MVP for an unofficial Wuthering Waves fan tool. A user uploads a character, echo, weapon, or stat screenshot. The backend extracts visible game data with GPT Vision or a local mock, the user corrects the structured result in the UI, and the app returns rule-based diagnoses plus a natural-language coaching report. The result can be saved to local SQLite history and exported/imported as JSON.

The MVP must work without an OpenAI API key by using sample extraction data. It must not include official game assets, crawler logic, SAM3/DINOv3 training, or anything that makes the tool look like an official Kuro Games service.

## Approach

Implement the complete MVP in one repository with separate `backend/` and `frontend/` directories. This is preferred over backend-only or frontend-only sequencing because the core risk is the end-to-end user flow: upload or mock extraction, manual correction, diagnosis, history, and export/import. Each layer will remain small and testable.

The repository folder remains `wawa-ai-coach`. The visible app title and documentation use `WuWa AI Coach`.

## Project Structure

```text
wawa-ai-coach/
  README.md
  .gitignore
  docs/
    superpowers/
      specs/
        2026-07-05-wuwa-ai-coach-design.md
  backend/
    pyproject.toml
    uv.lock
    main.py
    data/
      build_rules.json
      team_rules.json
      sample_extraction.json
    src/
      __init__.py
      database.py
      models.py
      vision.py
      parser.py
      evaluator.py
      report.py
      rules.py
      history.py
      export_import.py
      optional_ocr.py
      optional_local_vision.py
  frontend/
    package.json
    next.config.ts
    tsconfig.json
    postcss.config.mjs
    eslint.config.mjs
    src/
      app/
        globals.css
        layout.tsx
        page.tsx
      components/
        AppShell.tsx
        Dashboard.tsx
        ScreenshotAnalyzer.tsx
        ImageUploader.tsx
        ExtractionPanel.tsx
        EchoEditor.tsx
        DiagnosisResult.tsx
        CharacterPlanner.tsx
        TeamBuilder.tsx
        RulesManager.tsx
        HistoryPanel.tsx
        SettingsPanel.tsx
      lib/
        api.ts
        constants.ts
        types.ts
```

## Backend Design

The backend is a FastAPI app using Python 3.12, Pydantic as the shared data contract, and standard `sqlite3` for persistence. Python dependencies are managed with `uv`, using `uv venv --python 3.12` for `.venv` creation and `uv add` for dependency changes. `backend/src/models.py` defines the snapshot, extraction, rule, diagnosis, session, and analyze request/response models from the implementation prompt.

Modules:

- `database.py`: create SQLite connections and initialize `analysis_sessions` and `rules` tables at startup.
- `rules.py`: load build and team rules from JSON, validate them with Pydantic, and persist updated build rules.
- `vision.py`: expose `extract_from_image(image_bytes, filename)`. If `OPENAI_API_KEY` exists, call a vision-capable OpenAI model chosen by `OPENAI_MODEL`. If the key is missing or the call cannot return valid JSON, return a safe structured result with warnings; when no key is present, load `data/sample_extraction.json`.
- `parser.py`: extract the largest likely JSON block from model output and normalize extraction data.
- `evaluator.py`: choose the best build rule, score echoes, evaluate character state, and provide account/team placeholders.
- `report.py`: generate a local template report by default, with an optional OpenAI report path when an API key exists.
- `history.py`: save and read analysis sessions.
- `export_import.py`: export/import rules and history as JSON.
- `optional_ocr.py` and `optional_local_vision.py`: placeholder interfaces only.

API endpoints:

- `GET /health`
- `GET /rules`
- `POST /rules`
- `POST /vision/extract`
- `POST /analyze/echo`
- `POST /analyze/character`
- `POST /analyze/account`
- `POST /report`
- `GET /history`
- `POST /history`
- `GET /history/{session_id}`
- `GET /export`
- `POST /import`

## Frontend Design

The frontend is a Next.js, React, TypeScript, Tailwind CSS single-page tool. The first screen is the actual app, not a landing page. The default tab is `Analyzer`.

Tabs:

- `Dashboard`: recent analyses, current priorities, and recommended next actions.
- `Analyzer`: image upload, preview, GPT/mock extraction, JSON/raw text display, manual correction, diagnosis, report, JSON download, and history save.
- `Planner`: MVP placeholder for character growth priorities based on available data.
- `Teams`: MVP placeholder for owned-character team recommendations.
- `Rules`: view/edit/save build rule JSON.
- `History`: list saved sessions and inspect details.
- `Settings`: API base URL, API key guidance, JSON export/import, and unofficial fan-tool notices.

Component responsibilities:

- `ImageUploader`: file input and image preview.
- `ExtractionPanel`: structured JSON and raw visible text.
- `EchoEditor`: exactly five editable echo slots with sub-stat inputs.
- `DiagnosisResult`: grade, score, reasons, recommended actions, and natural-language report.
- `RulesManager`, `HistoryPanel`, `SettingsPanel`: CRUD-style interactions against the backend API.

The UI should be readable, practical, and responsive. It should use a restrained dashboard style, avoid nested cards, avoid official game assets, show "비공식 팬 도구" in the header, and keep all error states visible near the relevant action.

## Data Flow

1. The user opens the Analyzer tab.
2. The user uploads an image or starts with manual data.
3. `extractVision(file)` calls `POST /vision/extract`.
4. The backend returns `VisionExtractionResult`, using mock data if no API key is configured.
5. The UI displays JSON/raw text and editable snapshot fields.
6. The user runs diagnosis.
7. `analyzeCharacter(snapshot, fallbackRole)` calls `POST /analyze/character`.
8. The backend scores echoes and character state, then creates a report.
9. The user can save the result to history or export it as JSON.

## Error Handling

The app must not crash for normal MVP failure cases:

- Missing OpenAI API key: backend returns sample extraction with a warning.
- OpenAI failure: backend returns a structured warning response when possible.
- Invalid model JSON: backend attempts JSON-block extraction, then falls back to a valid extraction object with raw output and warnings.
- Backend connection failure: frontend shows a clear API connection error.
- Invalid rules JSON: frontend keeps the edited text and shows validation/save errors.
- History/import/export failure: frontend shows the failing operation and leaves current analysis state intact.

Uploaded images are not saved by default. The app saves structured session data only when the user explicitly clicks the history save action.

## Rule Evaluation

Echo scoring:

- Recommended set match: `+20`
- Main stat included in priority stats: `+25`
- Useful sub-stat: `+15` each
- Bad sub-stat: `-15` each
- Both Crit Rate and Crit DMG present: `+10`

Grade mapping:

- `score >= 85`: `excellent`
- `70-84`: `keep`
- `50-69`: `upgrade`
- `30-49`: `hold`
- `10-29`: `replace`
- `<10`: `discard`

Character evaluation checks weapon fit, echo set fit, key stats, role alignment, and next actions. Account and team evaluation remain explicit MVP placeholders with simple priority recommendations.

## Verification

Backend verification:

- `python -m compileall .`
- `uv run pytest -v`
- Start FastAPI with `uvicorn main:app --reload --port 8000`
- Confirm `GET /health` returns `{ "ok": true }`
- Confirm mock extraction works without `OPENAI_API_KEY`
- Confirm analyze, history, rules, export, and import endpoints work

Frontend verification:

- `npm run lint`
- `npm run build`
- Start with `npm run dev`
- Confirm Analyzer flow works with mock extraction and manual data
- Confirm rule edits change diagnosis output
- Confirm history save/read and JSON export/import work
- Inspect the browser UI for broken responsive layouts

## Non-Goals

- No SAM3 or DINOv3 implementation beyond placeholder adapter interfaces.
- No OCR dependency in the MVP path.
- No official game image, icon, or asset bundled in the repository.
- No scraping or automatic external guide ingestion.
- No login or cloud sync.
- No claim that this is an official Wuthering Waves or Kuro Games service.
