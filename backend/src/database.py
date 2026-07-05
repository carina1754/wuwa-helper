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
