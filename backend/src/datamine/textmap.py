from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from psycopg import Connection

from .paths import datamine_root


def _iter_textmap_files(root: Path) -> Iterable[Path]:
    yield from sorted((root / "Textmaps").rglob("*.json"))


def _lang_and_category(root: Path, path: Path) -> tuple[str, str]:
    parts = path.relative_to(root / "Textmaps").with_suffix("").parts
    lang = parts[0]
    category = "/".join(parts[1:]) if len(parts) > 1 else "_"
    return lang, category


def ingest_textmap(conn: Connection, root: Path | None = None) -> int:
    root = root or datamine_root()
    total = 0
    for path in _iter_textmap_files(root):
        lang, category = _lang_and_category(root, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            continue
        rows = [
            (lang, category, str(e["Id"]), e.get("Content") or "")
            for e in data
            if isinstance(e, dict) and "Id" in e
        ]
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM datamine_textmap WHERE lang = %s AND category = %s",
                (lang, category),
            )
            cur.executemany(
                "INSERT INTO datamine_textmap (lang, category, text_id, content) VALUES (%s, %s, %s, %s)",
                rows,
            )
        total += len(rows)
    conn.commit()
    return total


def resolve_text(conn: Connection, lang: str, key: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content FROM datamine_textmap WHERE lang = %s AND text_id = %s LIMIT 1",
            (lang, key),
        )
        row = cur.fetchone()
    return row["content"] if row else None
