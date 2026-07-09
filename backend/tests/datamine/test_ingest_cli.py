from __future__ import annotations

from src.datamine.ingest import run_ingest


def test_run_ingest_counts(conn):
    counts = run_ingest()
    assert counts == {
        "bindata_rows": 6,
        "textmap_rows": 2,
        "role_growth": 2,
        "characters": 1,
    }


def test_run_ingest_records_refresh_state(conn):
    run_ingest()
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM refresh_state WHERE source = 'datamine'")
        row = cur.fetchone()
    assert row is not None
    assert row["status"] == "ok"
