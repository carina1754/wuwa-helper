from __future__ import annotations

from pathlib import Path

import pytest

from src.database import get_connection, init_db

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "datamine"

_DATAMINE_TABLES = "datamine_bindata, datamine_textmap, sim_character, sim_role_growth"


@pytest.fixture
def conn(monkeypatch):
    # Scoped to tests that request `conn` (not autouse) so Task 1's
    # test_schema.py::test_datamine_root_default_points_at_repo_data — which
    # asserts the *default* (env-unset) datamine_root() — is unaffected.
    monkeypatch.setenv("DATAMINE_ROOT", str(FIXTURE_ROOT))
    init_db()  # base tables + datamine tables (wired into init_db in Task 1)
    with get_connection() as c:
        with c.cursor() as cur:
            cur.execute(f"TRUNCATE {_DATAMINE_TABLES}")
        c.commit()
        yield c
