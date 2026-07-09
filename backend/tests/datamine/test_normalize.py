from __future__ import annotations

from src.datamine.bindata import ingest_bindata
from src.datamine.normalize import build_sim_role_growth


def test_build_sim_role_growth(conn):
    ingest_bindata(conn)
    n = build_sim_role_growth(conn)
    assert n == 2
    with conn.cursor() as cur:
        cur.execute(
            "SELECT atk_ratio, def_ratio, hp_ratio FROM sim_role_growth WHERE level = 90 AND breach = 6"
        )
        row = cur.fetchone()
    assert row["atk_ratio"] == 125000
    assert row["def_ratio"] == 122222
    assert row["hp_ratio"] == 125000
