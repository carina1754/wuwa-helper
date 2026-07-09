from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

from psycopg import Connection
from psycopg.types.json import Jsonb

from .paths import datamine_root

logger = logging.getLogger(__name__)


def _iter_bindata_files(root: Path) -> Iterable[Path]:
    yield from sorted((root / "BinData").rglob("*.json"))


def _table_name(root: Path, path: Path) -> str:
    return path.relative_to(root / "BinData").with_suffix("").as_posix()


def _rows(data: object) -> list[tuple[str, object]]:
    if isinstance(data, list):
        return [(str(i), entry) for i, entry in enumerate(data)]
    return [("0", data)]


_NUL = chr(0)  # U+0000; PostgreSQL jsonb/text cannot store NUL characters.
_NUL_ESCAPE = chr(92) + "u0000"  # its JSON escape form in raw file text.


def _strip_nul(value: object) -> object:
    """Recursively drop NUL (U+0000) code points from decoded JSON.

    Some real BinData strings (binary blobs rendered as text, e.g. LockHint)
    contain NUL escapes that decode to U+0000, which Postgres jsonb/text rejects
    with UntranslatableCharacter. Stripping the NUL loses nothing meaningful.
    """
    if isinstance(value, str):
        return value.replace(_NUL, "")
    if isinstance(value, dict):
        return {_strip_nul(k): _strip_nul(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_nul(v) for v in value]
    return value


def ingest_bindata(conn: Connection, root: Path | None = None) -> int:
    root = root or datamine_root()
    total = 0
    for path in _iter_bindata_files(root):
        table = _table_name(root, path)
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("skipping unparseable BinData file %s: %s", path, exc)
            continue
        if _NUL_ESCAPE in text:
            data = _strip_nul(data)
        rows = _rows(data)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM datamine_bindata WHERE table_name = %s", (table,))
            cur.executemany(
                "INSERT INTO datamine_bindata (table_name, row_id, data) VALUES (%s, %s, %s)",
                [(table, rid, Jsonb(entry)) for rid, entry in rows],
            )
        total += len(rows)
    conn.commit()
    return total
