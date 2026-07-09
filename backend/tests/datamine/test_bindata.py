from __future__ import annotations

from src.datamine.bindata import ingest_bindata


def test_ingest_bindata_loads_all_files(conn):
    total = ingest_bindata(conn)
    # roleinfo(2) + baseproperty(2) + rolepropertygrowth(2)
    assert total == 6


def test_ingest_bindata_table_names_use_posix(conn):
    ingest_bindata(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT table_name FROM datamine_bindata ORDER BY table_name")
        tables = [r["table_name"] for r in cur.fetchall()]
    assert tables == ["property/baseproperty", "property/rolepropertygrowth", "role/roleinfo"]


def test_ingest_bindata_addressable_by_json_id(conn):
    ingest_bindata(conn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT data FROM datamine_bindata WHERE table_name = %s AND data->>'Id' = %s",
            ("role/roleinfo", "1108"),
        )
        row = cur.fetchone()
    assert row is not None
    assert row["data"]["ElementId"] == 1
    assert row["data"]["WeaponType"] == 2


def test_ingest_bindata_is_idempotent(conn):
    ingest_bindata(conn)
    total = ingest_bindata(conn)
    assert total == 6
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM datamine_bindata")
        assert cur.fetchone()["n"] == 6


def test_ingest_bindata_skips_unparseable(conn):
    # A malformed BinData file (real cases: furniture.json control-char, LFS stubs)
    # must be skipped, not abort the whole ingest — and must not disturb the good files.
    total = ingest_bindata(conn)
    assert total == 6  # 3 good fixture files still load; the broken file contributes 0
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM datamine_bindata WHERE table_name = %s",
            ("_broken/broken",),
        )
        assert cur.fetchone()["n"] == 0
        cur.execute(
            "SELECT COUNT(*) AS n FROM datamine_bindata WHERE table_name = %s",
            ("role/roleinfo",),
        )
        assert cur.fetchone()["n"] == 2
