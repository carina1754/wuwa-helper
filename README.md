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

Use Python 3.12 with `uv`.

```powershell
cd backend
uv venv --python 3.12
uv sync --dev
uv run uvicorn main:app --reload --port 8000
```

Optional environment variables:

```powershell
$env:OPENAI_API_KEY="..."
$env:OPENAI_MODEL="gpt-4.1-mini"
$env:DATABASE_URL="sqlite:///./wuwa_ai_coach.db"
```

If `OPENAI_API_KEY` is not set, `/vision/extract` returns `backend/data/sample_extraction.json` with a mock-mode warning.

To add backend dependencies, use `uv add` or `uv add --dev`; do not edit a `requirements.txt` file.

## Frontend Setup

Install Node.js with npm, then run:

```powershell
cd frontend
npm install
npm run dev
```

Set a custom backend URL if needed:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
```

If `npm` is not found immediately after installing Node.js on Windows, restart the terminal so `C:\Program Files\nodejs` is on `PATH`.

## Verification

Backend:

```powershell
cd backend
uv run python -m compileall main.py src tests
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
