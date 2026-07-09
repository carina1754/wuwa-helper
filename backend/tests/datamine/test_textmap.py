from __future__ import annotations

from src.datamine.textmap import ingest_textmap, resolve_text


def test_ingest_textmap_loads_langs(conn):
    total = ingest_textmap(conn)
    assert total == 2  # ko(1) + en(1)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT lang FROM datamine_textmap ORDER BY lang")
        langs = [r["lang"] for r in cur.fetchall()]
    assert langs == ["en", "ko"]


def test_ingest_textmap_category_from_path(conn):
    ingest_textmap(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT category FROM datamine_textmap")
        cats = {r["category"] for r in cur.fetchall()}
    assert cats == {"multi_text/MultiText"}


def test_resolve_text_string_key(conn):
    ingest_textmap(conn)
    assert resolve_text(conn, "ko", "RoleInfo_1108_Name") == "히유키"
    assert resolve_text(conn, "en", "RoleInfo_1108_Name") == "Hiyuki"


def test_resolve_text_missing_returns_none(conn):
    ingest_textmap(conn)
    assert resolve_text(conn, "ko", "Nope_Nonexistent") is None
