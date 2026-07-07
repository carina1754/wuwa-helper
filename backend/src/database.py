from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5432/wuwa_ai_coach"
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def _read_env_file_value(key: str) -> str | None:
    if not ENV_PATH.exists():
        return None
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return None


def database_url() -> str:
    return os.getenv("DATABASE_URL") or _read_env_file_value("DATABASE_URL") or DEFAULT_DATABASE_URL


@contextmanager
def get_connection() -> Iterator[Connection]:
    conn = psycopg.connect(database_url(), row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    name TEXT,
                    image TEXT,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_login_at TIMESTAMPTZ
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_accounts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    provider TEXT NOT NULL,
                    provider_account_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE (provider, provider_account_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS login_events (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                    provider TEXT NOT NULL,
                    email TEXT NOT NULL,
                    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                    created_at TEXT NOT NULL,
                    image_filename TEXT,
                    extraction_json TEXT NOT NULL,
                    diagnoses_json TEXT NOT NULL,
                    report TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rules (
                    id TEXT PRIMARY KEY,
                    character_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    rule_json TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS character_catalog (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    element TEXT,
                    weapon_type TEXT,
                    rarity INTEGER,
                    role TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    source TEXT,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS weapon_catalog (
                    id TEXT PRIMARY KEY,
                    name_ko TEXT NOT NULL,
                    weapon_type TEXT,
                    rarity INTEGER,
                    data_json TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS character_kit (
                    id TEXT PRIMARY KEY,
                    name_ko TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sonata_set (
                    id TEXT PRIMARY KEY,
                    name_ko TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS echo_catalog (
                    id TEXT PRIMARY KEY,
                    name_ko TEXT NOT NULL,
                    cost INTEGER,
                    data_json TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS team_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    core_character TEXT NOT NULL,
                    rule_json TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS pickup_schedule (
                    id TEXT PRIMARY KEY,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS game_updates (
                    id TEXT PRIMARY KEY,
                    version TEXT NOT NULL,
                    release_date_kst TEXT,
                    data_json TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS site_updates (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    version TEXT,
                    title_ko TEXT NOT NULL,
                    description_ko TEXT NOT NULL DEFAULT '',
                    data_json TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS refresh_state (
                    source TEXT PRIMARY KEY,
                    refreshed_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_sessions_user_id ON analysis_sessions(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_character_catalog_name ON character_catalog(name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_character_catalog_role ON character_catalog(role)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pickup_schedule_year_month ON pickup_schedule(year, month)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_game_updates_release_date ON game_updates(release_date_kst)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_site_updates_date ON site_updates(date)")
        conn.commit()