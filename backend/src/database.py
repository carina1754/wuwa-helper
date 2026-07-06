from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "wuwa_ai_coach.db"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"


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
        conn.execute(
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
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS team_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                core_character TEXT NOT NULL,
                rule_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pickup_schedule (
                id TEXT PRIMARY KEY,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                category TEXT NOT NULL,
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS game_updates (
                id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                release_date_kst TEXT,
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refresh_state (
                source TEXT PRIMARY KEY,
                refreshed_at TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_character_catalog_name ON character_catalog(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_character_catalog_role ON character_catalog(role)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pickup_schedule_year_month ON pickup_schedule(year, month)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_game_updates_release_date ON game_updates(release_date_kst)")
        _seed_rules(conn)
        _seed_character_catalog(conn)
        _seed_team_rules(conn)
        _seed_pickup_schedule(conn)
        _seed_game_updates(conn)
        _ensure_refresh_state(conn)
        conn.commit()


def _seed_rules(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
    if count:
        return

    path = DATA_DIR / "build_rules.json"
    if not path.exists():
        return

    rules = json.loads(path.read_text(encoding="utf-8"))
    for index, rule in enumerate(rules):
        rule_id = f"{rule['character_name'].strip().lower()}:{rule['role']}:{index}"
        conn.execute(
            """
            INSERT INTO rules (id, character_name, role, rule_json, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (
                rule_id,
                rule["character_name"],
                rule["role"],
                json.dumps(rule, ensure_ascii=False),
            ),
        )


def _seed_character_catalog(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM character_catalog").fetchone()[0]
    if count:
        return

    path = DATA_DIR / "character_catalog.json"
    if not path.exists():
        return

    characters = json.loads(path.read_text(encoding="utf-8"))
    for character in characters:
        conn.execute(
            """
            INSERT INTO character_catalog
            (id, name, element, weapon_type, rarity, role, data_json, source, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                character["id"],
                character["name"],
                character.get("element"),
                character.get("weapon_type"),
                character.get("rarity"),
                character["role"],
                json.dumps(character, ensure_ascii=False),
                character.get("source"),
            ),
        )


def _seed_team_rules(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM team_rules").fetchone()[0]
    if count:
        return

    path = DATA_DIR / "team_rules.json"
    if not path.exists():
        return

    rules = json.loads(path.read_text(encoding="utf-8"))
    for index, rule in enumerate(rules):
        conn.execute(
            """
            INSERT INTO team_rules (id, name, core_character, rule_json, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (
                f"{rule['name'].strip().lower()}:{index}",
                rule["name"],
                rule["core_character"],
                json.dumps(rule, ensure_ascii=False),
            ),
        )


def _seed_pickup_schedule(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM pickup_schedule").fetchone()[0]
    if count:
        return

    path = DATA_DIR / "pickup_schedule.json"
    if not path.exists():
        return

    items = json.loads(path.read_text(encoding="utf-8"))
    for item in items:
        conn.execute(
            """
            INSERT INTO pickup_schedule (id, year, month, category, data_json, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                item["id"],
                item["year"],
                item["month"],
                item["category"],
                json.dumps(item, ensure_ascii=False),
            ),
        )
    conn.execute(
        """
        INSERT OR IGNORE INTO refresh_state (source, refreshed_at, status, message)
        VALUES (?, datetime('now'), ?, ?)
        """,
        ("pcgamer_banners", "seeded", f"seed schedule={len(items)}"),
    )


def _seed_game_updates(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM game_updates").fetchone()[0]
    if count:
        return

    path = DATA_DIR / "game_updates.json"
    if not path.exists():
        return

    items = json.loads(path.read_text(encoding="utf-8"))
    for item in items:
        conn.execute(
            """
            INSERT INTO game_updates (id, version, release_date_kst, data_json, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (
                item["id"],
                item["version"],
                item.get("release_date_kst"),
                json.dumps(item, ensure_ascii=False),
            ),
        )


def _ensure_refresh_state(conn: sqlite3.Connection) -> None:
    pickup_count = conn.execute("SELECT COUNT(*) FROM pickup_schedule").fetchone()[0]
    if pickup_count:
        conn.execute(
            """
            INSERT OR IGNORE INTO refresh_state (source, refreshed_at, status, message)
            VALUES (?, datetime('now'), ?, ?)
            """,
            ("pcgamer_banners", "seeded", f"existing schedule={pickup_count}"),
        )
