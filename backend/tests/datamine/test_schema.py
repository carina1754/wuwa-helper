from __future__ import annotations

from pathlib import Path

from src.database import get_connection
from src.datamine.paths import datamine_root
from src.datamine.schema import init_datamine_schema


def test_datamine_root_default_points_at_repo_data():
    root = datamine_root()
    assert root.name == "WutheringWaves_Data-3.5"


def test_datamine_root_env_override(monkeypatch):
    monkeypatch.setenv("DATAMINE_ROOT", "/tmp/xyz")
    assert datamine_root() == Path("/tmp/xyz")


def test_init_datamine_schema_creates_tables():
    with get_connection() as conn:
        with conn.cursor() as cur:
            init_datamine_schema(cur)
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('datamine_bindata','datamine_textmap','sim_role_growth','sim_character')
                """
            )
            names = {r["table_name"] for r in cur.fetchall()}
        conn.commit()
    assert names == {"datamine_bindata", "datamine_textmap", "sim_role_growth", "sim_character"}
